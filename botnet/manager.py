import threading
from .config import Config
from .logging import get_logger
from .modules import get_module, reload_module
from .signals import module_loaded, module_unloaded, module_load, module_unload, \
    _request_list_commands, _list_commands, config_changed, on_exception
from .wrappers import ModuleWrapper


class Manager(object):
    """Main class which manages modules. This class loads and unloads modules
    and keeps them running by restarting the loops of the ones that have
    crashed.
    """

    # Class used for config
    config_class = Config

    def __init__(self, config_path=None):
        self.logger = get_logger(self)

        # List of ModuleWrapper objects, each with one module
        self.module_wrappers = []

        # Event used to stop the entire program
        self.stop_event = threading.Event()

        # Lock used to access the module_wrappers list
        self.wrappers_lock = threading.Lock()

        # Time between two updates
        self.deltatime = 1

        self.config = self.config_class()
        self.config_path = config_path
        if config_path:
            self.config.from_json_file(config_path)

        for module_name in self.config.get('modules', []):
            self.load_module_by_name(module_name)

        module_load.connect(self.on_module_load)
        module_unload.connect(self.on_module_unload)
        _request_list_commands.connect(self.on_request_list_commands)
        config_changed.connect(self.on_config_changed)

    def stop(self):
        """Stops the entire program."""
        self.logger.debug('Stop')
        with self.wrappers_lock:
            for wrapper in self.module_wrappers:
                wrapper.stop()
            self.stop_event.set()

    def get_wrapper(self, module_class):
        """Checks if the module is loaded. Returns ModuleWrapper or None on
        failure.
        """
        for wrapper in self.module_wrappers:
            if type(wrapper.module) is module_class:
                return wrapper
        return None

    def on_request_list_commands(self, sender, msg):
        """Handler for the _request_list_commands signal."""
        commands = []
        with self.wrappers_lock:
            for wrapper in self.module_wrappers:
                commands.extend(wrapper.module.get_all_commands())
        _list_commands.send(self, msg=msg, commands=commands)

    def on_config_changed(self, sender):
        """Handler for the config_changed signal."""
        try:
            with self.config.lock:
                if self.config_path:
                    self.config.to_json_file(self.config_path)
        except Exception as e:
            on_exception.send(self, e=e)

    def on_module_load(self, sender, name):
        """Handler for the module_load signal."""
        try:
            result = self.load_module_by_name(name)
            if result:
                with self.config.lock:
                    if not 'modules' in self.config:
                        self.config['modules'] = []
                    self.config['modules'].append(name)
                config_changed.send(self)
        except Exception as e:
            on_exception.send(self, e=e)

    def on_module_unload(self, sender, name):
        """Handler for the module_unload signal."""
        try:
            result = self.unload_module_by_name(name)
            if result:
                with self.config.lock:
                    if 'modules' in self.config:
                        self.config['modules'].remove(name)
                config_changed.send(self)
        except Exception as e:
            on_exception.send(self, e=e)

    def load_module_by_name(self, module_name):
        try:
            module = get_module(module_name)
            reload_module(module)
            module_class = getattr(module, 'mod')
        except (ImportError, AttributeError) as e:
            raise ValueError('Could not import module %s.' % module_name) from e
        return self.load_module(module_class)

    def unload_module_by_name(self, module_name):
        try:
            module = get_module(module_name)
            module_class = getattr(module, 'mod')
        except (ImportError, AttributeError) as e:
            raise ValueError('Could not import module %s.' % module_name) from e
        return self.unload_module(module_class)

    def load_module(self, module_class):
        """Loads a module. Returns a wrapper containing a loaded module or None
        if the module was not loaded.
        """
        self.logger.debug('Load module %s', module_class)
        with self.wrappers_lock:
            if not self.get_wrapper(module_class):
                module = module_class(self.config)
                wrapper = ModuleWrapper(module)
                self.module_wrappers.append(wrapper)
                module_loaded.send(self, cls=module_class)
                return wrapper
            return None

    def unload_module(self, module_class):
        """Unloads a module."""
        self.logger.debug('Unload module %s', module_class)
        with self.wrappers_lock:
            wrapper = self.get_wrapper(module_class)
            if wrapper is not None:
                wrapper.stop()
                self.module_wrappers.remove(wrapper)
                module_unloaded.send(self, cls=module_class)
                return True
        return False

    def run(self):
        """Periodically calls self.update."""
        while not self.stop_event.is_set():
            self.update()
            self.stop_event.wait(self.deltatime)

    def update(self):
        """(Re)starts modules which aren't running."""
        with self.wrappers_lock:
            if not self.stop_event.is_set():
                for wrapper in self.module_wrappers:
                    if not wrapper.is_alive():
                        wrapper.start()
