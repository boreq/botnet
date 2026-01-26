import threading

from .config import Config
from .logging import get_logger
from .message import IncomingPrivateMessage
from .modules import AuthContext
from .modules import BaseModule
from .modules.utils import get_ident_string
from .modules.utils import get_module
from .modules.utils import reload_module
from .signals import _list_commands
from .signals import _request_list_commands
from .signals import config_changed
from .signals import config_reload
from .signals import config_reloaded
from .signals import module_load
from .signals import module_loaded
from .signals import module_unload
from .signals import module_unloaded
from .signals import on_exception
from .wrappers import ModuleWrapper

type ModuleClass = type[BaseModule]


class Manager:
    """Main class which manages modules."""

    def __init__(self, config_path: str | None = None) -> None:
        self.logger = get_logger(self)

        # List of ModuleWrapper objects, each with one module
        self.module_wrappers: list[ModuleWrapper] = []

        # Event used to stop the entire program
        self.stop_event = threading.Event()

        # Lock used to access the module_wrappers list
        self.wrappers_lock = threading.Lock()

        # Handle config, load modules defined there
        self.config: Config = Config()
        self.config_path = config_path
        if config_path:
            self.config.from_json_file(config_path)

        module_load.connect(self.on_module_load)
        module_unload.connect(self.on_module_unload)
        _request_list_commands.connect(self.on_request_list_commands)
        config_reload.connect(self.on_config_reload)
        config_changed.connect(self.on_config_changed)

        for module_name in self.config.get('modules', []):
            self.load_module_by_name(module_name)

    def stop(self) -> None:
        """Stops all modules and then the entire program."""
        self.logger.debug('Stop')
        with self.wrappers_lock:
            for wrapper in self.module_wrappers:
                wrapper.stop()
            self.stop_event.set()

    def on_request_list_commands(self, sender: object, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
        """Handler for the _request_list_commands signal."""
        commands: set[str] = set()
        with self.wrappers_lock:
            for wrapper in self.module_wrappers:
                try:
                    commands.update(wrapper.module.get_all_commands(msg, auth))
                except Exception as e:
                    on_exception.send(self, e=e)
        _list_commands.send(self, msg=msg, auth=auth, commands=commands)

    def on_config_changed(self, sender: object) -> None:
        """Handler for the config_changed signal."""
        self.logger.debug('Received config_changed signal')
        try:
            with self.config.lock:
                if self.config_path:
                    self.config.to_json_file(self.config_path)
        except Exception as e:
            on_exception.send(self, e=e)

    def on_config_reload(self, sender: object) -> None:
        """Handler for the config_reload signal."""
        self.logger.debug('Received config_reload signal')
        try:
            with self.config.lock:
                if self.config_path:
                    self.config.from_json_file(self.config_path)
                    config_reloaded.send(self)
        except Exception as e:
            on_exception.send(self, e=e)

    def on_module_load(self, sender: object, module_name: str) -> None:
        """Handler for the module_load signal."""
        self.logger.debug(f'Received module_load signal for module {module_name}.')
        try:
            if self.load_module_by_name(module_name) is not None:
                with self.config.lock:
                    if 'modules' not in self.config:
                        self.config['modules'] = []
                    self.config['modules'].append(module_name)
                config_changed.send(self)
        except Exception as e:
            on_exception.send(self, e=e)

    def on_module_unload(self, sender: object, module_name: str) -> None:
        """Handler for the module_unload signal."""
        self.logger.debug(f'Received module_unload signal for module {module_name}.')
        try:
            if self.unload_module_by_name(module_name):
                with self.config.lock:
                    if 'modules' in self.config:
                        self.config['modules'].remove(module_name)
                config_changed.send(self)
        except Exception as e:
            on_exception.send(self, e=e)

    def load_module_by_name(self, module_name: str) -> ModuleWrapper | None:
        """Loads a module by name. Returns a wrapper containing a loaded module
        or None if the module was not loaded because it is already loaded.
        """
        try:
            module = get_module(module_name)
            module = reload_module(module)
            module_class = getattr(module, 'mod')
        except (ImportError, AttributeError) as e:
            raise ValueError('Could not import module %s.' % module_name) from e
        return self.load_module(module_class)

    def unload_module_by_name(self, module_name: str) -> bool:
        """Unloads a module. Returns False if the module wasn't loaded and
        therefore there was nothing to do.
        """
        try:
            module = get_module(module_name)
            module_class = getattr(module, 'mod')
        except (ImportError, AttributeError) as e:
            raise ValueError('Could not import module %s.' % module_name) from e
        return self.unload_module(module_class)

    def load_module(self, module_class: ModuleClass) -> ModuleWrapper | None:
        """Loads a module. Returns a wrapper containing a loaded module or None
        if the module was not loaded because it is already loaded.
        """
        self.logger.debug('Load module %s', module_class)
        with self.wrappers_lock:
            if self._get_wrapper(module_class) is None:
                module = module_class(self.config)
                wrapper = ModuleWrapper(module)
                wrapper.start()
                self.module_wrappers.append(wrapper)
                self.logger.debug('Loaded module %s', module_class)
                module_loaded.send(self, cls=module_class)
                return wrapper
        self.logger.debug('Module %s is already loaded so it was not loaded again', module_class)
        return None

    def unload_module(self, module_class: ModuleClass) -> bool:
        """Unloads a module. Returns False if the module wasn't loaded and
        therefore there was nothing to do."""
        self.logger.debug('Unload module %s', module_class)
        with self.wrappers_lock:
            wrapper = self._get_wrapper(module_class)
            if wrapper is not None:
                wrapper.stop()
                self.module_wrappers.remove(wrapper)
                self.logger.debug('Unloaded module %s', module_class)
                module_unloaded.send(self, cls=module_class)
                return True
        self.logger.debug('Module %s is not loaded so it was not unloaded', module_class)
        return False

    def run(self) -> None:
        """Method which can be used to block until the self.stop method has
        been called. There is nothing to do in the Manager because all modules
        are separate and if they want to do anything (generate signals out of
        their own initiative and not in response to other signals) they have to
        run in a separate threads anyway to avoid blocking everything else.
        """
        self.stop_event.wait()

    def _get_wrapper(self, module_class: ModuleClass) -> ModuleWrapper | None:
        """Checks if a module is loaded. Returns ModuleWrapper or None on
        failure.
        """
        for wrapper in self.module_wrappers:
            if wrapper.name == get_ident_string(module_class):
                return wrapper
        return None
