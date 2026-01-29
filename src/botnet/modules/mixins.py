import inspect
import re
from collections.abc import Callable
from dataclasses import Field
from dataclasses import asdict
from enum import Enum
from typing import Any
from typing import ClassVar
from typing import Generic
from typing import Protocol
from typing import TypeVar

import dacite

from ..config import Config
from ..message import IncomingPrivateMessage
from ..message import Message
from ..message import MessageCommand
from ..signals import auth_message_in
from ..signals import config_changed
from ..signals import message_in
from ..signals import on_exception
from .base import AuthContext
from .base import BaseModule
from .decorators import _ATTR_AUTH_MESSAGE_HANDLER
from .decorators import _ATTR_COMMAND_NAME
from .decorators import _ATTR_MESSAGE_HANDLER
from .decorators import _ATTR_PREDICATES


class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


_MODULE_CONFIG_KEY = 'module_config'


MODULE_CONFIG_DATACLASS = TypeVar('MODULE_CONFIG_DATACLASS', bound=DataclassInstance)
ANOTHER_MODULE_CONFIG_DATACLASS = TypeVar('ANOTHER_MODULE_CONFIG_DATACLASS', bound=DataclassInstance)
SOME_MODULE_CONFIG_DATACLASS = TypeVar('SOME_MODULE_CONFIG_DATACLASS', bound=DataclassInstance)


class ConfigMixin(Generic[MODULE_CONFIG_DATACLASS], BaseModule):
    # A module is expected to store the config in
    # config['module_config'][config_namespace][config_name]
    config_namespace: str | None = None
    config_name: str | None = None

    # Even though we accept parameter MODULE_CONFIG_DATACLASS for typechecking
    # we still need to have this information at runtime to be able to construct
    # the object.
    config_class: type[MODULE_CONFIG_DATACLASS] | None = None

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._config = config

    def get_config(self) -> MODULE_CONFIG_DATACLASS:
        """Returns the config for this module. This does not exhibit any of the
        previous weird magic behaviour with looking for the config in different
        places.
        """
        if self.config_namespace is None or self.config_name is None or self.config_class is None:
            raise ValueError('inheriting classes must set config_namespace, config_name and config_class')

        with self._config.lock:
            return self._load_config(self.config_namespace, self.config_name, self.config_class)

    def change_config(self, f: Callable[[MODULE_CONFIG_DATACLASS], None]) -> None:
        """Allows changing the config for this module which will then be automagically saved."""
        if self.config_namespace is None or self.config_name is None or self.config_class is None:
            raise ValueError('inheriting classes must set config_namespace, config_name and config_class')

        with self._config.lock:
            module_config = self._load_config(self.config_namespace, self.config_name, self.config_class)
            f(module_config)
            if _MODULE_CONFIG_KEY not in self._config:
                self._config[_MODULE_CONFIG_KEY] = {}
            if self.config_namespace not in self._config[_MODULE_CONFIG_KEY]:
                self._config[_MODULE_CONFIG_KEY][self.config_namespace] = {}
            self._config['module_config'][self.config_namespace][self.config_name] = asdict(module_config)
            config_changed.send(self)

    def peek_loaded_config_for_module(self, namespace: str, module: str, config_dataclass: type[ANOTHER_MODULE_CONFIG_DATACLASS]) -> ANOTHER_MODULE_CONFIG_DATACLASS:
        """Peeks config for a different module. In principle this is considered harmful and yet here we are."""
        with self._config.lock:
            return self._load_config(namespace, module, config_dataclass)

    def _load_config(self, namespace: str, module_name: str, config_dataclass: type[SOME_MODULE_CONFIG_DATACLASS]) -> SOME_MODULE_CONFIG_DATACLASS:
        if _MODULE_CONFIG_KEY in self._config \
                and namespace in self._config[_MODULE_CONFIG_KEY] \
                and module_name in self._config[_MODULE_CONFIG_KEY][namespace]:
            data = self._config[_MODULE_CONFIG_KEY][namespace][module_name]
        else:
            data = {}
        return dacite.from_dict(data_class=config_dataclass, data=data, config=dacite.Config(cast=[Enum], strict=True))


BoundCommandHandler = Callable[[IncomingPrivateMessage, AuthContext], None]
BoundMessageHandler = Callable[[Message], None]
BoundAuthMessageHandler = Callable[[Message, AuthContext], None]


class MessageDispatcherMixin(BaseModule):
    """Dispatches messages received via `message_in` and `auth_message_in`
    signals to appropriate methods.

    When a message is received via the `message_in` signal it is dispatched to
    handlers marked with the decorators such as:
        - `@message_handler`
        - `@privmsg_message_handler`
        - etc

    When a message is received via the `auth_message_in` signal it is
    dispatched to handlers marked with the decorators such as:
        - `@auth_message_handler`
        - `@auth_privmsg_message_handler`
        - etc

    When a PRIVMSG message is received via the `auth_message_in` signal and it
    contains a .command inside of it's text it is dispatched to handlers marked
    with the appropriate 'command_handler' decorator.
    """

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        auth_message_in.connect(self._on_auth_message_in)
        message_in.connect(self._on_message_in)

    def get_command_prefix(self) -> str:
        """This method should return the command prefix."""
        raise NotImplementedError

    def get_all_commands(self, msg: IncomingPrivateMessage, auth: AuthContext) -> set[str]:
        rw = super().get_all_commands(msg, auth)
        for handler in self._get_all_command_handlers():
            if self._command_predicates_pass(handler, msg, auth):
                rw.add(getattr(handler, _ATTR_COMMAND_NAME))
        return rw

    def get_help_for_command(self, command_name: str, msg: IncomingPrivateMessage, auth: AuthContext) -> list[str]:
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

    def get_command_name(self, msg: IncomingPrivateMessage) -> str | None:
        """Extracts the command name from a PRIVMSG message."""
        command_prefix = self.get_command_prefix()
        if not msg.text.s.startswith(command_prefix):
            return None
        cmd_name = msg.text.s.split(' ')[0]
        cmd_name = cmd_name.strip(command_prefix)
        if len(cmd_name) == 0:
            return None
        return cmd_name

    def _on_auth_message_in(self, sender: object, msg: Message, auth: AuthContext) -> None:
        try:
            self._dispatch_auth_message(msg, auth)
        except Exception as e:
            on_exception.send(self, e=e)

    def _dispatch_auth_message(self, msg: Message, auth: AuthContext) -> None:
        for handler in self._get_all_auth_message_handlers():
            handler(msg, auth)

        if msg.command == MessageCommand.PRIVMSG.value:
            privmsg = IncomingPrivateMessage.new_from_message(msg)
            command_name = self.get_command_name(privmsg)
            if command_name is not None:
                for command_handler in self._get_command_handlers(command_name):
                    if self._command_predicates_pass(command_handler, privmsg, auth):
                        command_handler(privmsg, auth)

    def _on_message_in(self, sender: object, msg: Message) -> None:
        try:
            self._dispatch_message(msg)
        except Exception as e:
            on_exception.send(self, e=e)

    def _dispatch_message(self, msg: Message) -> None:
        for handler in self._get_all_message_handlers():
            handler(msg)

    def _get_command_handlers(self, command_name: str) -> list[BoundCommandHandler]:
        handlers: list[BoundCommandHandler] = []
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if getattr(method, _ATTR_COMMAND_NAME, None) == command_name:
                handlers.append(method)
        return handlers

    def _get_all_command_handlers(self) -> list[BoundCommandHandler]:
        handlers: list[BoundCommandHandler] = []
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if getattr(method, _ATTR_COMMAND_NAME, None) is not None:
                handlers.append(method)
        return handlers

    def _command_predicates_pass(self, handler: BoundCommandHandler, msg: IncomingPrivateMessage, auth: AuthContext) -> bool:
        for predicate in getattr(handler, _ATTR_PREDICATES, []):
            if not predicate(self, msg, auth):
                return False
        return True

    def _get_all_message_handlers(self) -> list[BoundMessageHandler]:
        handlers: list[BoundMessageHandler] = []
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if getattr(method, _ATTR_MESSAGE_HANDLER, None) is not None:
                handlers.append(method)
        return handlers

    def _get_all_auth_message_handlers(self) -> list[BoundAuthMessageHandler]:
        handlers: list[BoundAuthMessageHandler] = []
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if getattr(method, _ATTR_AUTH_MESSAGE_HANDLER, None) is not None:
                handlers.append(method)
        return handlers
