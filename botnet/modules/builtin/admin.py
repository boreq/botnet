import datetime
from collections import namedtuple
from ...message import Message
from ...signals import message_out, admin_message_in
from .. import BaseResponder
from ..cache import MemoryCache


DeferredWhois = namedtuple('DeferredWhois', ['nick', 'on_complete'])


class WhoisMixin(object):

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

    config_namespace = 'botnet'
    config_name = 'admin'

    def handle_privmsg(self, msg):
        super(Admin, self).handle_msg(msg)
        admin_list = self.config_get('admins', [])
        if msg.nickname in admin_list:
            def on_complete(whois_data):
                if whois_data['authenticated']:
                    admin_message_in.send(self, msg=msg)
            self.whois_schedule(msg.nickname, on_complete)


mod = Admin
