import threading
from dataclasses import dataclass
from typing import Any

from ...config import Config
from ...message import IncomingPrivateMessage
from ...signals import config_reload
from ...signals import config_reloaded
from ...signals import module_load
from ...signals import module_loaded
from ...signals import module_unload
from ...signals import module_unloaded
from .. import Args
from .. import AuthContext
from .. import BaseResponder
from .. import command
from .. import only_admins
from .. import parse_command
from ..utils import get_ident_string


@dataclass()
class AdminConfig:
    pass


class Admin(BaseResponder[AdminConfig]):
    """Implements a few administrative commands."""

    config_namespace = 'botnet'
    config_name = 'admin'
    config_class = AdminConfig

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        module_loaded.connect(self._on_module_loaded)
        module_unloaded.connect(self._on_module_unloaded)
        config_reloaded.connect(self._on_config_reloaded)
        # Since there is no threading involved in the signal distribution the
        # last message which triggered a command will simply be on top of those
        # lists
        self._load_commands: list[IncomingPrivateMessage] = []
        self._unload_commands: list[IncomingPrivateMessage] = []
        self._config_reload_commands: list[IncomingPrivateMessage] = []

    @command('module_load')
    @only_admins()
    @parse_command([('module_names', '+')])
    def admin_command_module_load(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Loads a module.

        Syntax: module_load MODULE_NAME ...
        """
        for name in args['module_names']:
            self._load_module(msg, name)

    @command('module_unload')
    @only_admins()
    @parse_command([('module_names', '+')])
    def admin_command_module_unload(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Unloads a module.

        Syntax: module_unload MODULE_NAME ...
        """
        for name in args['module_names']:
            self._unload_module(msg, name)

    @command('module_reload')
    @only_admins()
    @parse_command([('module_names', '+')])
    def admin_command_module_reload(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Unloads and loads a module back.

        Syntax: module_reload MODULE_NAME ...
        """
        for name in args['module_names']:
            self._reload_module(msg, name)

    @command('config_reload')
    @only_admins()
    def admin_command_config_reload(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
        """Reloads the config.

        Syntax: config_reload
        """
        self._reload_config(msg)

    def _load_module(self, msg: IncomingPrivateMessage, name: str) -> None:
        self._load_commands.append(msg)
        module_load.send(self, name=name)

    def _unload_module(self, msg: IncomingPrivateMessage, name: str) -> None:
        self._unload_commands.append(msg)
        module_unload.send(self, name=name)

    def _reload_module(self, msg: IncomingPrivateMessage, name: str) -> None:
        def f() -> None:
            self._unload_module(msg, name)
            self._load_module(msg, name)

        t = threading.Thread(target=f)
        t.start()

    def _reload_config(self, msg: IncomingPrivateMessage) -> None:
        self._config_reload_commands.append(msg)
        config_reload.send(self)

    def _on_module_loaded(self, sender: Any, cls: type) -> None:
        try:
            msg = self._load_commands.pop()
            self.respond(msg, 'Loaded module %s' % get_ident_string(cls))
        except IndexError:
            pass

    def _on_module_unloaded(self, sender: Any, cls: type) -> None:
        try:
            msg = self._unload_commands.pop()
            self.respond(msg, 'Unloaded module %s' % get_ident_string(cls))
        except IndexError:
            pass

    def _on_config_reloaded(self, sender: Any) -> None:
        try:
            msg = self._config_reload_commands.pop()
            self.respond(msg, 'Config reloaded')
        except IndexError:
            pass


mod = Admin
