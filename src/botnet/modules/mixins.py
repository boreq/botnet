import re
import inspect
from ..signals import message_in, auth_message_in, on_exception, config_changed
from ..config import Config
from .base import BaseModule, AuthContext
from .decorators import _ATTR_COMMAND_NAME, _ATTR_PREDICATES
from ..message import Message
from collections.abc import Callable


_SENTI = object()
_ADMIN_GROUP_NAME = 'admin'


def _iterate_dict(d, key):
    """Allows to search a dict using a key.which.looks.like.this instead
    of passing complex lambda expressions to functions.
    """
    location = d
    for i, part in enumerate(key.split('.')):
        if isinstance(location, dict):
            location = location[part]
            yield location
        else:
            raise ValueError('''Tried to access a value which is not a dict. '''
                             '''Failed for key "{}"'''.format(key))


class ConfigMixin(BaseModule):
    """Adds various config related methods to a module. Allows the user to
    access config keys by passing a string delimited by dots.

        self.register_config('my_namespace', 'common')
        self.register_config('my_namespace', 'my_module')
        self.config_set('one.two.three', 'value')
        self.config_get('one.two.three')
    """

    config: Config
    _config_defaults: list[Config]
    _config_locations: list[tuple[str, str]]

    def __init__(self, config: Config) -> None:
        super().__init__(config)

        # actual Config object
        self.config = config
        # list of dicts with default configuration values
        self._config_defaults = []
        # list of tuples (namespace, name)
        self._config_locations = []

    def _get_config_key(self, config, key):
        return 'module_config.{}.{}.{}'.format(config[0], config[1], key)

    def register_default_config(self, config: Config):
        """Adds a default config. Default configs are queried for requested
        values in a reverse order in which they were registered in case a value
        is missing from the actual config.
        """
        self._config_defaults.append(config)

    def register_config(self, namespace, name):
        """Adds a location of the configuration values used by this module
        in the config.
        """
        self._config_locations.append((namespace, name))

    def config_get(self, key, default=_SENTI, auto=_SENTI):
        """Tries to get the value assigned to `key` from the registered configs.
        Raises KeyError if a key does not exist in the dictionary,
        Raises ValueError if a value which a key tries to subscript is not a dict.

        key: key in the following format: 'one.two.three'
        default: returns this value instead of rising a KeyError if a key is not
                 in the config.
        auto: key will be set in to that value if it is not present in the
              config. And the new value will be returned. Takes precedence over
              default so using those two options together is pointless.
        """
        # configs
        with self.config.lock:
            for config in reversed(self._config_locations):
                actual_key = self._get_config_key(config, key)
                try:
                    return next(reversed(list(_iterate_dict(self.config, actual_key))))
                except KeyError:
                    continue

        # defaults
        for config in reversed(self._config_defaults):
            try:
                return next(reversed(list(_iterate_dict(config, key))))
            except KeyError:
                continue

        if auto is not _SENTI:
            self.config_set(key, auto)
            return self.config_get(key)

        if default is not _SENTI:
            return default

        raise KeyError

    def config_set(self, key, value):
        """Sets a value in the last registered location in the config."""
        if not self._config_locations:
            raise ValueError('No config locations. Call register_config first.')

        actual_key = self._get_config_key(self._config_locations[-1], key)

        # walk
        with self.config.lock:
            location = self.config
            parts = actual_key.split('.')
            for i, part in enumerate(parts[:-1]):
                if isinstance(location, dict):
                    if part not in location:
                        location[part] = {}
                    location = location[part]
                else:
                    raise ValueError("""Tried to change a value which is not a dict. """
                                     """Failed for key '{}'""".format(key))
            location[parts[-1]] = value
        # indicate that the config was modified
        config_changed.send(self)
        return True

    def config_append(self, key, value):
        """Alias for
            self.config_get(key, auto=[]).append(value)
        """
        try:
            self.config_get(key, auto=[]).append(value)
            config_changed.send(self)
        except AttributeError as e:
            raise AttributeError('Value for a key "{}" is not a list'.format(key)) from e
        return True


class MessageDispatcherMixin(BaseModule):
    """Dispatches messages received via `auth_message_in` signal to appropriate
    methods.

    When a message is received via the `auth_message_in` signal:
        - All messages are dispatched to `handle_msg` and `handle_auth_msg`.
        - All PRIVMSG messages are dispatched to `handle_privmsg` and `handle_auth_privmsg`.
        - If a message starts with a command prefix defined in the config it
          will also be sent to all handlers marked with a matching command
          decorator.
    """

    def __init__(self, config):
        super().__init__(config)
        auth_message_in.connect(self._on_auth_message_in)
        message_in.connect(self._on_message_in)

    def handle_msg(self, msg: Message) -> None:
        """Called when a message is received."""
        pass

    def handle_privmsg(self, msg: Message) -> None:
        """Called when a message with a PRIVMSG command is received."""
        pass

    def handle_auth_msg(self, msg: Message, auth: AuthContext) -> None:
        """Called when a message is received."""
        pass

    def handle_auth_privmsg(self, msg: Message, auth: AuthContext) -> None:
        """Called when a message with a PRIVMSG command is received."""
        pass

    def get_command_prefix(self) -> str:
        """This method should return the command prefix."""
        raise NotImplementedError

    def get_all_commands(self, msg: Message, auth: AuthContext) -> list[str]:
        command_names: set[str] = set()
        for handler in self._get_all_command_handlers():
            if self._command_predicates_pass(handler, msg, auth):
                command_names.add(getattr(handler, _ATTR_COMMAND_NAME))
        return list(command_names)

    def get_help_for_command(self, command_name: str, msg: Message, auth: AuthContext) -> list[str]:
        help_texts: list[str] = []
        for handler in self._get_command_handlers(command_name):
            if self._command_predicates_pass(handler, msg, auth):
                # Header
                rw = 'Module %s, help for `%s`: ' % (self.__class__.__name__, command_name)

                # Docstring
                help_text = handler.__doc__
                if help_text:
                    rw += ' '.join(help_text.splitlines())
                else:
                    rw += 'No help available.'

                rw = re.sub(' +', ' ', rw)
                help_texts.append(rw)
        return help_texts

    def get_command_name(self, priv_msg: Message) -> str | None:
        """Extracts the command name from a PRIVMSG message."""
        command_prefix = self.get_command_prefix()
        if not priv_msg.params[-1].startswith(command_prefix):
            return None
        cmd_name = priv_msg.params[-1].split(' ')[0]
        cmd_name = cmd_name.strip(self.get_command_prefix())
        return cmd_name

    def _on_auth_message_in(self, sender, msg: Message, auth: AuthContext) -> None:
        try:
            self._dispatch_auth_message(msg, auth)
        except Exception as e:
            on_exception.send(self, e=e)

    def _on_message_in(self, sender, msg: Message) -> None:
        try:
            self._dispatch_message(msg)
        except Exception as e:
            on_exception.send(self, e=e)

    def _dispatch_auth_message(self, msg: Message, auth: AuthContext) -> None:
        self.handle_auth_msg(msg, auth)

        if msg.command == 'PRIVMSG':
            self.handle_auth_privmsg(msg, auth)

            command_name = self.get_command_name(msg)
            if command_name is not None:
                for handler in self._get_command_handlers(command_name):
                    if self._command_predicates_pass(handler, msg, auth):
                        handler(msg, auth)

    def _dispatch_message(self, msg: Message) -> None:
        self.handle_msg(msg)

        if msg.command == 'PRIVMSG':
            self.handle_privmsg(msg)

    def _get_command_handlers(self, command_name: str) -> list[Callable]:
        """Gets a list of command handlers which match this command name."""
        handlers: list[Callable] = []
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if getattr(method, _ATTR_COMMAND_NAME, None) == command_name:
                handlers.append(method)
        return handlers

    def _get_all_command_handlers(self) -> list[Callable]:
        """Gets a list of all command handlers."""
        handlers: list[Callable] = []
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if getattr(method, _ATTR_COMMAND_NAME, None) is not None:
                handlers.append(method)
        return handlers

    def _command_predicates_pass(self, handler: Callable, msg: Message, auth: AuthContext) -> bool:
        """Returns a handler for a command."""
        for predicate in getattr(handler, _ATTR_PREDICATES, []):
            if not predicate(self, msg, auth):
                return False
        return True
