import datetime
from dataclasses import dataclass
from typing import Any, Callable
from ...message import Message, IncomingPrivateMessage, Nick
from ...signals import message_out, auth_message_in
from .. import AuthContext, BaseResponder
from ..lib import MemoryCache
from ..base import BaseModule
from ...config import Config


@dataclass
class DeferredWhois:
    nick: Nick
    on_complete: Callable[[dict[str, Any]], None]


class WhoisMixin(BaseModule):
    """Provides a way of requesting and handling WHOIS data received from the
    IRC server. WHOIS data should be requested using the function
    WhoisMixin.whois_schedule.

    Keys which *may* be present in the whois_data dictionary:

        {
            'nick',            # nick
            'user',            # username
            'host',            # host
            'real_name',       # real name
            'server',          # url of a server to which the user is connected
            'server_info,      # string with additional information about the server
            'away',            # away message set by the user, present if the user is /away
            'nick_identified', # nick the user has identified for
        }

    """

    whois_cache_timeout = 60 * 15

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._whois_cache: MemoryCache[Nick, dict] = MemoryCache(self.whois_cache_timeout)
        self._whois_deferred: list[DeferredWhois] = []
        self._whois_current: dict[Nick, dict[str, Any]] = {}

    def handler_rpl_whoisuser(self, msg: Message) -> None:
        """Start of WHOIS."""
        nick = Nick(msg.params[1])
        self._whois_current[nick] = {
            'time': datetime.datetime.now(),
            'nick': msg.params[1],
            'user': msg.params[2],
            'host': msg.params[3],
            'real_name': msg.params[5],
        }

    def handler_rpl_whoisserver(self, msg: Message) -> None:
        """WHOIS server."""
        nick = Nick(msg.params[1])
        if nick in self._whois_current:
            self._whois_current[nick]['server'] = msg.params[2]
            self._whois_current[nick]['server_info'] = msg.params[3]

    def handler_rizon_rpl_whoisidentified(self, msg: Message) -> None:
        """WHOIS identification on Rizon."""
        nick = Nick(msg.params[1])
        if nick in self._whois_current:
            self._whois_current[nick]['nick_identified'] = msg.params[2]

    def handler_freenode_rpl_whoisidentified(self, msg: Message) -> None:
        """WHOIS identification on Freenode."""
        nick = Nick(msg.params[1])
        if nick in self._whois_current:
            self._whois_current[nick]['nick_identified'] = msg.params[1]

    def handler_rpl_away(self, msg: Message) -> None:
        """WHOIS away message."""
        nick = Nick(msg.params[1])
        if nick in self._whois_current:
            self._whois_current[nick]['away'] = msg.params[2]

    def handler_rpl_endofwhois(self, msg: Message) -> None:
        """End of WHOIS."""
        nick = Nick(msg.params[1])
        if nick not in self._whois_current:
            return
        self._whois_cache.set(nick, self._whois_current.pop(nick))
        self._whois_run_deferred()

    def handler_part(self, msg: Message) -> None:
        """Handler for PART."""
        assert msg.nickname is not None
        nick = Nick(msg.nickname)
        self._whois_cache.delete(nick)

    def handler_quit(self, msg: Message) -> None:
        """Handler for QUIT."""
        assert msg.nickname is not None
        nick = Nick(msg.nickname)
        self._whois_cache.delete(nick)

    def whois_schedule(self, nick: Nick, on_complete: Callable[[dict[str, Any]], None]) -> None:
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

    def handle_msg(self, msg: Message) -> None:
        # Dispatch to the handlers
        code = msg.command_code
        if code is not None:
            handler_name = 'handler_%s' % code.name.lower()
        else:
            handler_name = 'handler_%s' % msg.command.lower()
        func = getattr(self, handler_name, None)
        if func is not None:
            func(msg)


class Auth(WhoisMixin, BaseResponder):
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
                            "contact": [
                                "nick"
                            ],
                            groups: ["admin"]
                        }
                    ]
                }
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'auth'

    def __init__(self, config: Config) -> None:
        super().__init__(config)

    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        super().handle_privmsg(msg)

        def on_complete(whois_data: dict[str, Any]) -> None:
            for person in self.config_get('people', []):
                uuid = person.get('uuid')
                groups = person.get('groups')
                for authorisation in person.get('authorisations', []):
                    match authorisation['kind']:
                        case 'irc':
                            if whois_data.get('nick_identified', None) != authorisation['nick']:
                                continue
                            self._emit_auth_message_in(msg, uuid, groups)
                            return
                        case 'matrix':
                            if whois_data.get('server', None) != 'matrix.hackint.org':
                                continue
                            if whois_data.get('real_name', None) != authorisation['nick']:
                                continue
                            self._emit_auth_message_in(msg, uuid, groups)
                            return
                        case _:
                            raise Exception('unknown authorisation kind: {}'.format(authorisation['kind']))
            self._emit_auth_message_in(msg, None, [])

        self.whois_schedule(msg.sender, on_complete)

    def _emit_auth_message_in(self, msg: IncomingPrivateMessage, uuid: str | None, groups: list[str]) -> None:
        auth_context = AuthContext(uuid, groups)
        auth_message_in.send(self, msg=msg, auth=auth_context)


mod = Auth
