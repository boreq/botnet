import datetime
from collections import namedtuple
from ...message import Message
from ...signals import message_out, admin_message_in
from .. import BaseResponder
from ..cache import MemoryCache


DeferredWhois = namedtuple('DeferredWhois', ['nick', 'on_complete'])


class WhoisMixin(object):
    """Provides a way of requesting and handling WHOIS data received from the 
    IRC server. WHOIS data should be requested using the function
    WhoisMixin.whois_schedule.

    Keys which *may* be present in the whois_data dictionary:

        [
            'nick',       # nick
            'user',       # username
            'host',       # host
            'real_name',  # real name
            'channels',   # list of channels the user is in
            'server',     # url of a server to which the user is connected
            'server_info, # string with additional information about the server
            'away',       # away message set by the user, present if the user is /away
        ]

    """

    whois_cache_timeout = 60

    def __init__(self, config):
        super(WhoisMixin, self).__init__(config)
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
        if not 'channels' in self._whois_current[msg.params[1]]:
            self._whois_current[msg.params[1]]['channels'] = []
        self._whois_current[msg.params[1]]['channels'].extend(msg.params[2:])

    def handler_rpl_whoisserver(self, msg):
        self._whois_current[msg.params[1]]['server'] = msg.params[2]
        self._whois_current[msg.params[1]]['server_info'] = msg.params[3]

    def handler_rpl_away(self, msg):
        self._whois_current[msg.params[1]]['away'] = msg.params[2]

    def handler_rpl_endofwhois(self, msg):
        """End of WHOIS."""
        if not msg.params[1] in self._whois_current:
            return
        self._whois_cache.set(msg.params[1], self._whois_current.pop(msg.params[1]))
        self._whois_run_deferred()

    def whois_schedule(self, nick, on_complete):
        """Schedules an action to be completed when the whois for the nick is
        available.
        nick: nick of the user for whom whois is required.
        on_complete: function which will be called when the whois will be
                     available.
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
        """Loops over the deferred functions and launched those for which WHOIS
        data is available.
        """
        for i in reversed(range(len(self._whois_deferred))):
            d = self._whois_deferred[i]
            data = self._whois_cache.get(d.nick)
            if data is not None:
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


class Admin(WhoisMixin, BaseResponder):
    """Implements a few administrative commands. Resends commands received
    in the `message_in` signal which originate from one of the admins in the
    `admin_message_in` signal. That way all modules which are subscribed to
    the `admin_message_in` signal can implement commands which are available
    only for the bot admins. An admin is a user whose nick is present in the
    list `admins` in the module config and who has authenticated for that nick
    on the IRC network.

    Example module config:

        "botnet": {
            "admin": {
                "admins": ["nick1", "nick2"]
            }
        }
    """

    config_namespace = 'botnet'
    config_name = 'admin'

    def handle_privmsg(self, msg):
        super(Admin, self).handle_msg(msg)
        admin_list = self.config_get('admins', [])
        if msg.nickname in admin_list:
            def on_complete(whois_data):
                if whois_data.get('authenticated', None):
                    admin_message_in.send(self, msg=msg)
            self.whois_schedule(msg.nickname, on_complete)


mod = Admin
