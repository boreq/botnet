import datetime
from collections import namedtuple
from dataclasses import dataclass
from ...message import Message
from ...signals import message_out, auth_message_in
from .. import BaseResponder
from ..lib import MemoryCache


DeferredWhois = namedtuple('DeferredWhois', ['nick', 'on_complete'])


class WhoisMixin(object):
    """Provides a way of requesting and handling WHOIS data received from the
    IRC server. WHOIS data should be requested using the function
    WhoisMixin.whois_schedule.

    Keys which *may* be present in the whois_data dictionary:

        {
            'nick',            # nick
            'user',            # username
            'host',            # host
            'real_name',       # real name
            'channels',        # list of channels the user is in
            'server',          # url of a server to which the user is connected
            'server_info,      # string with additional information about the server
            'away',            # away message set by the user, present if the user is /away
            'nick_identified', # nick the user has identified for
        }

    """

    whois_cache_timeout = 120

    def __init__(self, config):
        super().__init__(config)
        self._whois_cache = MemoryCache(self.whois_cache_timeout)
        self._whois_deferred = []
        self._whois_current = {}

    def handler_rpl_whoisuser(self, msg):
        """Start of WHOIS."""
        self._whois_current[msg.params[1]] = {
            'time': datetime.datetime.now(),
            'nick': msg.params[1],
            'user': msg.params[2],
            'host': msg.params[3],
            'real_name': msg.params[5],
        }

    def handler_rpl_whoischannels(self, msg):
        """WHOIS channels."""
        if msg.params[1] in self._whois_current:
            if 'channels' not in self._whois_current[msg.params[1]]:
                self._whois_current[msg.params[1]]['channels'] = []
            self._whois_current[msg.params[1]]['channels'].extend(msg.params[2:])

    def handler_rpl_whoisserver(self, msg):
        """WHOIS server."""
        if msg.params[1] in self._whois_current:
            self._whois_current[msg.params[1]]['server'] = msg.params[2]
            self._whois_current[msg.params[1]]['server_info'] = msg.params[3]

    def handler_rizon_rpl_whoisidentified(self, msg):
        """WHOIS identification on Rizon."""
        if msg.params[1] in self._whois_current:
            self._whois_current[msg.params[1]]['nick_identified'] = msg.params[2]

    def handler_freenode_rpl_whoisidentified(self, msg):
        """WHOIS identification on Freenode."""
        if msg.params[1] in self._whois_current:
            self._whois_current[msg.params[1]]['nick_identified'] = msg.params[1]

    def handler_rpl_away(self, msg):
        """WHOIS away message."""
        if msg.params[1] in self._whois_current:
            self._whois_current[msg.params[1]]['away'] = msg.params[2]

    def handler_rpl_endofwhois(self, msg):
        """End of WHOIS."""
        if msg.params[1] not in self._whois_current:
            return
        self._whois_cache.set(msg.params[1], self._whois_current.pop(msg.params[1]))
        self._whois_run_deferred()

    def whois_schedule(self, nick, on_complete):
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

    def _whois_run_deferred(self):
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

    def _whois_perform(self, nick):
        """Sends a message with the WHOIS command."""
        msg = Message(command='WHOIS', params=[nick])
        message_out.send(self, msg=msg)

    def handle_msg(self, msg):
        # Dispatch to the handlers
        code = msg.command_code()
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
                            "nicks": [
                                {
                                    "kind": "irc",
                                    "nick": "nick"
                                },
                                {
                                    "kind": "matrix",
                                    "nick": "@nick:example.com"
                                }
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

    def __init__(self, config):
        super().__init__(config)

    def handle_privmsg(self, msg):
        super().handle_privmsg(msg)

        def on_complete(whois_data):
            for person in self.config_get('people', []):
                groups = person.get('groups')
                for nick_data in person.get('nicks', []):
                    match nick_data['kind']:
                        case 'irc':
                            if whois_data.get('nick_identified', None) != nick_data['nick']:
                                continue
                            self._emit_auth_message_in(msg, nick, groups)
                        case 'matrix':
                            if whois_data.get('server', None) != 'matrix.hackint.org':
                                continue
                            if whois_data.get('real_name', None) != nick_data['nick']:
                                continue
                            self._emit_auth_message_in(msg, nick, groups)
                        case _:
                            raise Exception('unknown nick kind: {}'.format(nick_data['kind']))

        self.whois_schedule(msg.nickname, on_complete)

    def _emit_auth_message_in(self, msg, nick: Nick, groups: list[str]) -> None:
        for group in groups:
            auth_context = AuthContext(group, nick)
            auth_message_in.send(self, msg=msg, auth=auth_context)


@dataclass
class AuthContext:
    group: str
    nick: Nick


@dataclass
class Nick:
    kind: str
    nick: str


mod = Auth
