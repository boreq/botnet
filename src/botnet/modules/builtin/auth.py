from dataclasses import dataclass
from typing import Callable

from ...codes import Code
from ...config import Config
from ...message import IncomingKick
from ...message import IncomingPart
from ...message import IncomingQuit
from ...message import Message
from ...message import Nick
from ...modules import kick_message_handler
from ...modules import message_handler
from ...modules import part_message_handler
from ...modules import quit_message_handler
from ...modules import reply_handler
from ...signals import auth_message_in
from ...signals import message_out
from .. import AuthContext
from .. import BaseResponder
from ..base import BaseModule
from ..lib import MemoryCache


@dataclass()
class WhoisResponse:
    nick: str | None              # nick
    user: str | None              # username
    host: str | None              # host
    real_name: str | None         # real name
    server: str | None            # url of a server to which the user is connected
    server_info: str | None       # string with additional information about the server
    away: str | None              # away message set by the user, present if the user is /away
    nick_identified: str | None   # nick the user has identified for


@dataclass()
class DeferredWhois:
    nick: Nick
    on_complete: Callable[[WhoisResponse], None]


class WhoisMixin(BaseModule):
    """Provides a way of requesting and handling WHOIS data received from the
    IRC server. WHOIS data should be requested using the function
    WhoisMixin.whois_schedule.
    """

    whois_cache_timeout = 60 * 15

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._whois_cache: MemoryCache[Nick, WhoisResponse] = MemoryCache(self.whois_cache_timeout)
        self._whois_deferred: list[DeferredWhois] = []
        self._whois_current: dict[Nick, WhoisResponse] = {}

    @reply_handler(Code.RPL_WHOISUSER)
    def handler_rpl_whoisuser(self, msg: Message) -> None:
        nick = Nick(msg.params[1])
        self._whois_current[nick] = WhoisResponse(
            nick=msg.params[1],
            user=msg.params[2],
            host=msg.params[3],
            real_name=msg.params[5],
            server=None,
            server_info=None,
            away=None,
            nick_identified=None,
        )

    @reply_handler(Code.RPL_WHOISSERVER)
    def handler_rpl_whoisserver(self, msg: Message) -> None:
        nick = Nick(msg.params[1])
        if nick in self._whois_current:
            self._whois_current[nick].server = msg.params[2]
            self._whois_current[nick].server_info = msg.params[3]

    @reply_handler(Code.RIZON_RPL_WHOISIDENTIFIED)
    def handler_rizon_rpl_whoisidentified(self, msg: Message) -> None:
        nick = Nick(msg.params[1])
        if nick in self._whois_current:
            self._whois_current[nick].nick_identified = msg.params[2]

    @reply_handler(Code.FREENODE_RPL_WHOISIDENTIFIED)
    def handler_freenode_rpl_whoisidentified(self, msg: Message) -> None:
        nick = Nick(msg.params[1])
        if nick in self._whois_current:
            self._whois_current[nick].nick_identified = msg.params[1]

    @reply_handler(Code.RPL_AWAY)
    def handler_rpl_away(self, msg: Message) -> None:
        nick = Nick(msg.params[1])
        if nick in self._whois_current:
            self._whois_current[nick].away = msg.params[2]

    @reply_handler(Code.RPL_ENDOFWHOIS)
    def handler_rpl_endofwhois(self, msg: Message) -> None:
        nick = Nick(msg.params[1])
        if nick not in self._whois_current:
            return
        self._whois_cache.set(nick, self._whois_current.pop(nick))
        self._whois_run_deferred()

    @part_message_handler()
    def handler_part(self, msg: IncomingPart) -> None:
        self._whois_cache.delete(msg.nick)

    @quit_message_handler()
    def handler_quit(self, msg: IncomingQuit) -> None:
        self._whois_cache.delete(msg.nick)

    @kick_message_handler()
    def handler_kick(self, msg: IncomingKick) -> None:
        self._whois_cache.delete(msg.kickee)

    def whois_schedule(self, nick: Nick, on_complete: Callable[[WhoisResponse], None]) -> None:
        """Schedules an action to be completed when the whois for the nick is
        available.

        nick: nick of the user for whom whois is required.
        on_complete: function which will be called when the whois will be
                     available. Required function signature:
                     void (*function)(dict whois_data)
        """
        whois_data = self._whois_cache.get(nick)
        if whois_data is not None:
            on_complete(whois_data)
        else:
            data = DeferredWhois(nick, on_complete)
            self._whois_deferred.append(data)
            self._whois_perform(data.nick)

    def _whois_run_deferred(self) -> None:
        """Loops over the deferred functions and launches those for which WHOIS
        data is available.
        """
        for i in reversed(range(len(self._whois_deferred))):
            d = self._whois_deferred[i]
            data = self._whois_cache.get(d.nick)
            if data is not None:
                self.logger.debug('Running deferred %s', d.on_complete)
                d.on_complete(data)
                self._whois_deferred.pop(i)

    def _whois_perform(self, nick: Nick) -> None:
        """Sends a message with the WHOIS command."""
        msg = Message(command='WHOIS', params=[nick.s])
        message_out.send(self, msg=msg)


@dataclass()
class AuthConfig:
    people: list[AuthConfigPerson]

    def __post_init__(self) -> None:
        uuids = set([person.uuid for person in self.people])
        if len(uuids) != len(self.people):
            raise ValueError('duplicate person uuid in auth config')


@dataclass()
class AuthConfigPerson:
    uuid: str
    authorisations: list[AuthConfigAuthorisation]
    contact: list[str]
    groups: list[str]

    def __post_init__(self) -> None:
        if self.uuid == '':
            raise ValueError('person uuid cannot be empty')

        if len(self.authorisations) == 0:
            raise ValueError('person must have at least one authorisation otherwise they will never be identified')


@dataclass()
class AuthConfigAuthorisation:
    kind: str
    nick: str

    def __post_init__(self) -> None:
        if self.kind not in ['irc', 'matrix']:
            raise ValueError('unknown authorisation kind: {}'.format(self.kind))
        match self.kind:
            case 'irc':
                if not Nick(self.nick):
                    raise ValueError('invalid irc nick in authorisation: {}'.format(self.nick))
            case 'matrix':
                if not self.nick.startswith('@') or ':' not in self.nick:
                    raise ValueError('invalid matrix nick in authorisation: {}'.format(self.nick))


class Auth(WhoisMixin, BaseResponder[AuthConfig]):
    """Resends messages coming in on `message_in` on `auth_message_in` after
    attaching authorisation-related context to them.

    Thanks to this module other modules may easily check if users are
    authorised to perform certain actions.

    Example module config:

        "botnet": {
            "auth": {
                "people": [
                        {
                            "uuid": "someperson",
                            "authorisations": [
                                {
                                    "kind": "irc",
                                    "nick": "nick"
                                },
                                {
                                    "kind": "matrix",
                                    "nick": "@nick:example.com"
                                }
                            ],
                            "contact": ["nick"],
                            groups: ["admin"]
                        }
                    ]
                }
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'auth'
    config_class = AuthConfig

    def __init__(self, config: Config) -> None:
        super().__init__(config)

    @message_handler()
    def handle_msg(self, msg: Message) -> None:
        def on_complete(whois_data: WhoisResponse) -> None:
            config = self.get_config()
            for person in config.people:
                for authorisation in person.authorisations:
                    match authorisation.kind:
                        case 'irc':
                            if whois_data.nick_identified != authorisation.nick:
                                continue
                            self._emit_auth_message_in(msg, person.uuid, person.groups)
                            return
                        case 'matrix':
                            if whois_data.server != 'matrix.hackint.org':
                                continue
                            if whois_data.real_name != authorisation.nick:
                                continue
                            self._emit_auth_message_in(msg, person.uuid, person.groups)
                            return
                        case _:
                            raise Exception('unknown authorisation kind: {}'.format(authorisation.kind))
            self._emit_auth_message_in(msg, None, [])

        if msg.nickname is not None:
            self.whois_schedule(Nick(msg.nickname), on_complete)

    def _emit_auth_message_in(self, msg: Message, uuid: str | None, groups: list[str]) -> None:
        auth_context = AuthContext(uuid, groups)
        auth_message_in.send(self, msg=msg, auth=auth_context)


mod = Auth
