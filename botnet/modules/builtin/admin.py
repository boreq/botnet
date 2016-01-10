import datetime
import threading
from collections import namedtuple
from ...message import Message
from ...signals import message_out, admin_message_in, module_load, module_unload, \
    module_loaded, module_unloaded, config_reload, config_reloaded
from .. import BaseResponder
from ..lib import MemoryCache, parse_command


DeferredWhois = namedtuple('DeferredWhois', ['nick', 'on_complete'])


class WhoisMixin(object):
    """Provides a way of requesting and handling WHOIS data received from the 
    IRC server. WHOIS data should be requested using the function
    WhoisMixin.whois_schedule.

    Keys which *may* be present in the whois_data dictionary:

        [
            'nick',            # nick
            'user',            # username
            'host',            # host
            'real_name',       # real name
            'channels',        # list of channels the user is in
            'server',          # url of a server to which the user is connected
            'server_info,      # string with additional information about the server
            'away',            # away message set by the user, present if the user is /away
            'nick_identified', # nick the user has identified for
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
        if msg.params[1] in self._whois_current:
            if not 'channels' in self._whois_current[msg.params[1]]:
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
        if not msg.params[1] in self._whois_current:
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
        """Loops over the deferred functions and launched those for which WHOIS
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

    def __init__(self, config):
        super(Admin, self).__init__(config)
        module_loaded.connect(self.on_module_loaded)
        module_unloaded.connect(self.on_module_unloaded)
        config_reloaded.connect(self.on_config_reloaded)
        # Since there is no threading involved in the signal distribution
        # the last message which triggered a command will simply be on top of
        # those lists
        self.load_commands = []
        self.unload_commands = []
        self.config_reload = []

    def load(self, msg, name):
        self.load_commands.append(msg)
        module_load.send(self, name=name)

    def unload(self, msg, name):
        self.unload_commands.append(msg)
        module_unload.send(self, name=name)

    def reload(self, msg, name):
        def f():
            self.unload(msg, name)
            self.load(msg, name)

        t = threading.Thread(target=f)
        t.start()

    @parse_command([('module_names', '*')])
    def admin_command_module_load(self, msg, args):
        """Loads a module.

        Syntax: module_load MODULE_NAME ...
        """
        for name in args.module_names:
            self.load(msg, name)

    @parse_command([('module_names', '*')])
    def admin_command_module_unload(self, msg, args):
        """Unloads a module.

        Syntax: module_unload MODULE_NAME ...
        """
        for name in args.module_names:
            self.unload(msg, name)

    @parse_command([('module_names', '*')])
    def admin_command_module_reload(self, msg, args):
        """Unloads and loads a module back.

        Syntax: module_reload MODULE_NAME ...
        """
        for name in args.module_names:
            self.reload(msg, name)

    def admin_command_config_reload(self, msg):
        """Reloads the config.

        Syntax: config_reload
        """
        self.config_reload.append(msg)
        config_reload.send(self)

    def on_module_loaded(self, sender, cls):
        try:
            msg = self.load_commands.pop()
            self.respond(msg, 'Loaded module %s' % cls)
        except IndexError as e:
            pass

    def on_module_unloaded(self, sender, cls):
        try:
            msg = self.unload_commands.pop()
            self.respond(msg, 'Unloaded module %s' % cls)
        except IndexError as e:
            pass

    def on_config_reloaded(self, sender):
        try:
            msg = self.config_reload.pop()
            self.respond(msg, 'Config reloaded')
        except IndexError as e:
            pass

    def handle_privmsg(self, msg):
        super(Admin, self).handle_msg(msg)
        admin_list = self.config_get('admins', [])
        if msg.nickname in admin_list:
            def on_complete(whois_data):
                if whois_data.get('nick_identified', None):
                    admin_message_in.send(self, msg=msg)
            self.whois_schedule(msg.nickname, on_complete)


mod = Admin
