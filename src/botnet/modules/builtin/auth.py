from dataclasses import dataclass
from typing import Callable

from botnet.modules.decorators import nick_message_handler

from ...codes import Code
from ...config import Config
from ...message import IncomingKick
from ...message import IncomingNick
from ...message import IncomingPart
from ...message import IncomingQuit
from ...message import Message
from ...message import Nick
from ...message import Target
from ...modules import kick_message_handler
from ...modules import message_handler
from ...modules import part_message_handler
from ...modules import quit_message_handler
from ...modules import reply_handler
from ...signals import auth_message_in
from ...signals import message_out
from ...signals import with_group as with_group_signal
from ...signals import with_user as with_user_signal
from .. import AuthContext
from .. import BaseResponder
from ..base import BaseModule
from ..lib import MemoryCache

_HACKINT_MATRIX_SERVER = 'matrix.hackint.org'


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

    @nick_message_handler()
    def handler_nick(self, msg: IncomingNick) -> None:
        self._whois_cache.delete(msg.old_nick)
        self._whois_cache.delete(msg.new_nick)

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
class AuthConfigAuthorisationLoggedInAs:
    nick: str

    def __post_init__(self) -> None:
        try:
            Nick(self.nick)
        except Exception as e:
            raise ValueError('logged_in_as authorisation nick must be a valid nick') from e


@dataclass()
class AuthConfigAuthorisationMatrix:
    nick: str

    def __post_init__(self) -> None:
        if not self.nick.startswith('@'):
            raise ValueError('matrix authorisation nick must start with @')
        if ':' not in self.nick:
            raise ValueError('matrix authorisation nick must contain a server part separated by a colon')


@dataclass()
class AuthConfigAuthorisationNickAndHost:
    nick: str
    host: str

    def __post_init__(self) -> None:
        try:
            Nick(self.nick)
        except Exception as e:
            raise ValueError('logged_in_as authorisation nick must be a valid nick') from e

        if self.host == '':
            raise ValueError('nick_and_host authorisation host cannot be empty')


@dataclass()
class AuthConfigAuthorisation:
    logged_in_as: AuthConfigAuthorisationLoggedInAs | None
    matrix: AuthConfigAuthorisationMatrix | None
    nick_and_host: AuthConfigAuthorisationNickAndHost | None

    def __post_init__(self) -> None:
        counter = 0
        if self.logged_in_as is not None:
            counter += 1
        if self.matrix is not None:
            counter += 1
        if self.nick_and_host is not None:
            counter += 1
        if counter != 1:
            raise ValueError('exactly one authorisation kind must be set')


class AuthorisedUser:
    """Handle passed to a `with_user` closure."""

    def __init__(self, nick: Nick, auth: AuthContext, send: Callable[[Target, str], None]) -> None:
        self.nick = nick
        self.auth = auth
        self._send = send

    def message(self, text: str) -> None:
        """Messages this nick only if it is currently authorised."""
        if self.auth.uuid is not None:
            self._send(Target(self.nick), text)


class AuthorisedGroup:
    """Handle passed to a `with_group` closure."""

    def __init__(self, group: str, people: list[AuthConfigPerson], message_person: Callable[[AuthConfigPerson, str], None]) -> None:
        self.group = group
        self.people = people
        self._message_person = message_person

    def message_all(self, text: str) -> None:
        """Messages the members of the group on their authorised nicks only."""
        for person in self.people:
            self._message_person(person, text)


WithGroupClosure = Callable[[AuthorisedGroup], None]

WithUserClosure = Callable[[AuthorisedUser], None]


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
                                    "logged_in_as": {
                                        "nick": "nick"
                                    }
                                },
                                {
                                    "nick_and_host": {
                                        "nick": "nick",
                                        "host": "1.2.3.4"
                                    }
                                },
                                {
                                    "matrix": {
                                        "username": "@nick:example.com"
                                    }
                                }
                            ],
                            "contact": ["nick"],
                            "groups": ["admin"]
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
        with_group_signal.connect(self.on_with_group)
        with_user_signal.connect(self.on_with_user)

    @message_handler()
    def handle_msg(self, msg: Message) -> None:
        def on_complete(whois_data: WhoisResponse) -> None:
            auth = self._auth_context_for_whois(whois_data)
            self._emit_auth_message_in(msg, auth.uuid, auth.groups)

        if msg.nickname is not None:
            self.whois_schedule(Nick(msg.nickname), on_complete)

    def on_with_group(self, sender: object, group_uuid: str, with_group: WithGroupClosure) -> None:
        """Handler for the `with_group` signal."""
        people = [person for person in self.get_config().people if group_uuid in person.groups]
        with_group(AuthorisedGroup(group_uuid, people, self._message_person))

    def on_with_user(self, sender: object, user_uuid: str, with_user: WithUserClosure) -> None:
        """Handler for the `with_user` signal."""
        for person in self.get_config().people:
            if person.uuid == user_uuid:
                self._with_person_contacts(person, with_user)
                return

    def _with_person_contacts(self, person: AuthConfigPerson, with_user: WithUserClosure) -> None:
        for contact in person.contact:
            nick = Nick(contact)
            self.whois_schedule(nick, self._resolve_user(person, nick, with_user))

    def _message_person(self, person: AuthConfigPerson, text: str) -> None:
        self._with_person_contacts(person, lambda user: user.message(text))

    def _resolve_user(self, person: AuthConfigPerson, nick: Nick, with_user: WithUserClosure) -> Callable[[WhoisResponse], None]:
        def on_complete(whois_data: WhoisResponse) -> None:
            if any(self._authorisation_matches_whois(a, whois_data) for a in person.authorisations):
                auth = AuthContext(person.uuid, person.groups)
            else:
                auth = AuthContext(None, [])
            with_user(AuthorisedUser(nick, auth, self.message))
        return on_complete

    def _auth_context_for_whois(self, whois_data: WhoisResponse) -> AuthContext:
        for person in self.get_config().people:
            for authorisation in person.authorisations:
                if self._authorisation_matches_whois(authorisation, whois_data):
                    return AuthContext(person.uuid, person.groups)
        return AuthContext(None, [])

    def _authorisation_matches_whois(self, authorisation: AuthConfigAuthorisation, whois_data: WhoisResponse) -> bool:
        if authorisation.logged_in_as is not None:
            if whois_data.nick_identified != authorisation.logged_in_as.nick:
                return False
            return True

        if authorisation.nick_and_host is not None:
            if whois_data.nick is None:
                return False
            if Nick(whois_data.nick) != Nick(authorisation.nick_and_host.nick):
                return False
            if whois_data.host != authorisation.nick_and_host.host:
                return False
            return True

        if authorisation.matrix is not None:
            if whois_data.server != _HACKINT_MATRIX_SERVER:
                return False
            if whois_data.real_name != authorisation.matrix.nick:
                return False
            return True

        raise Exception('unknown authorisation kind')

    def _emit_auth_message_in(self, msg: Message, uuid: str | None, groups: list[str]) -> None:
        auth_context = AuthContext(uuid, groups)
        auth_message_in.send(self, msg=msg, auth=auth_context)


mod = Auth
