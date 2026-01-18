import threading
from ...signals import module_load, module_unload, module_loaded, \
    module_unloaded, config_reload, config_reloaded
from .. import BaseResponder
from ..lib import parse_command


class Admin(BaseResponder):
    """Implements a few administrative commands."""

    config_namespace = 'botnet'
    config_name = 'admin'

    def __init__(self, config):
        super().__init__(config)
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
        except IndexError:
            pass

    def on_module_unloaded(self, sender, cls):
        try:
            msg = self.unload_commands.pop()
            self.respond(msg, 'Unloaded module %s' % cls)
        except IndexError:
            pass

    def on_config_reloaded(self, sender):
        try:
            msg = self.config_reload.pop()
            self.respond(msg, 'Config reloaded')
        except IndexError:
            pass


mod = Admin
