import threading
from ...message import Message
from ...signals import module_load, module_unload, module_loaded, \
    module_unloaded, config_reload, config_reloaded
from .. import BaseResponder, command, only_admins
from ..lib import parse_command


class Admin(BaseResponder):
    """Implements a few administrative commands."""

    config_namespace = 'botnet'
    config_name = 'admin'

    def __init__(self, config) -> None:
        super().__init__(config)
        module_loaded.connect(self._on_module_loaded)
        module_unloaded.connect(self._on_module_unloaded)
        config_reloaded.connect(self._on_config_reloaded)
        # Since there is no threading involved in the signal distribution the
        # last message which triggered a command will simply be on top of those
        # lists
        self._load_commands: list[Message] = []
        self._unload_commands: list[Message] = []
        self._config_reload_commands: list[Message] = []

    @command('module_load')
    @only_admins()
    @parse_command([('module_names', '*')])
    def admin_command_module_load(self, msg, args):
        """Loads a module.

        Syntax: module_load MODULE_NAME ...
        """
        for name in args.module_names:
            self._load_module(msg, name)

    @command('module_unload')
    @only_admins()
    @parse_command([('module_names', '*')])
    def admin_command_module_unload(self, msg, args):
        """Unloads a module.

        Syntax: module_unload MODULE_NAME ...
        """
        for name in args.module_names:
            self._unload_module(msg, name)

    @command('module_reload')
    @only_admins()
    @parse_command([('module_names', '*')])
    def admin_command_module_reload(self, msg, args):
        """Unloads and loads a module back.

        Syntax: module_reload MODULE_NAME ...
        """
        for name in args.module_names:
            self._reload_module(msg, name)

    @command('config_reload')
    @only_admins()
    def admin_command_config_reload(self, msg):
        """Reloads the config.

        Syntax: config_reload
        """
        self._reload_config(msg)

    def _load_module(self, msg: Message, name: str) -> None:
        self._load_commands.append(msg)
        module_load.send(self, name=name)

    def _unload_module(self, msg: Message, name: str) -> None:
        self._unload_commands.append(msg)
        module_unload.send(self, name=name)

    def _reload_module(self, msg, name) -> None:
        def f():
            self.unload(msg, name)
            self.load(msg, name)

        t = threading.Thread(target=f)
        t.start()

    def _reload_config(self, msg: Message, name: str) -> None:
        self._config_reload_commands.append(msg)
        config_reload.send(self)

    def _on_module_loaded(self, sender, cls) -> None:
        try:
            msg = self._load_commands.pop()
            self.respond(msg, 'Loaded module %s' % cls)
        except IndexError:
            pass

    def _on_module_unloaded(self, sender, cls) -> None:
        try:
            msg = self._unload_commands.pop()
            self.respond(msg, 'Unloaded module %s' % cls)
        except IndexError:
            pass

    def _on_config_reloaded(self, sender) -> None:
        try:
            msg = self._config_reload_commands.pop()
            self.respond(msg, 'Config reloaded')
        except IndexError:
            pass


mod = Admin
