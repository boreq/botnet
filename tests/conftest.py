import logging
import os
import tempfile
import time
from typing import Any
from typing import Callable
from typing import Generic
from typing import Optional
from typing import Protocol
from typing import TypeVar

import pytest

from botnet import BaseModule
from botnet.config import Config
from botnet.message import Message
from botnet.modules import AuthContext
from botnet.signals import _request_list_commands
from botnet.signals import auth_message_in
from botnet.signals import clear_state
from botnet.signals import config_changed
from botnet.signals import config_reload
from botnet.signals import config_reloaded
from botnet.signals import message_in
from botnet.signals import message_out
from botnet.signals import module_load
from botnet.signals import module_loaded
from botnet.signals import module_unload
from botnet.signals import module_unloaded
from botnet.signals import on_exception

log_format = '%(asctime)s %(levelname)s %(name)s: %(message)s'
log_level = logging.DEBUG
logging.basicConfig(format=log_format, level=log_level)


@pytest.fixture()
def tmp_file(request: pytest.FixtureRequest) -> str:
    fd, path = tempfile.mkstemp()

    def teardown() -> None:
        os.close(fd)
        os.remove(path)

    request.addfinalizer(teardown)
    return path


class MakePrivmsgFixture(Protocol):
    def __call__(self, text: str, nick: Optional[str] = None, target: Optional[str] = None) -> Message:
        ...


@pytest.fixture()
def make_privmsg() -> Callable[[str, str, str], Message]:
    """Provides a PRIVMSG message factory."""
    def f(text: str, nick: str = 'nick', target: str = '#channel') -> Message:
        return Message(
            prefix='%s!~user@1-2-3-4.example.com' % nick,
            command='PRIVMSG',
            params=[target, text]
        )
    return f


@pytest.fixture()
def rec_msg() -> Callable[[Message], None]:
    """Provides a function used for sending messages via message_in signal."""
    def f(msg: Message) -> None:
        message_in.send(None, msg=msg)
    return f


@pytest.fixture()
def rec_auth_msg() -> Callable[[Message], None]:
    """Provides a function used for sending messages via auth_message_in signal."""
    def f(msg: Message) -> None:
        auth_message_in.send(None, msg=msg)
    return f


@pytest.fixture()
def resource_path() -> Callable[[str], str]:
    """Provides a function used for creating paths to resources."""
    def f(path: str) -> str:
        dirpath = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(dirpath, 'resources', path)
    return f


@pytest.fixture()
def clear_signal_state() -> None:
    clear_state()


class Trap(object):
    def __init__(self, signal: Any) -> None:
        self.trapped: list[dict[str, Any]] = []
        signal.connect(self.on_signal)

    def on_signal(self, sender: Any, **kwargs: Any) -> None:
        self.trapped.append(kwargs)

    def reset(self) -> None:
        self.trapped = []

    def wait(self, assertion: Callable[[list[dict[str, Any]]], None], max_seconds: int = 1) -> None:
        for i in range(max_seconds * 10):
            if i != 0:
                time.sleep(0.1)

            try:
                assertion(self.trapped)
            except AssertionError:
                continue

            return
        assertion(self.trapped)


@pytest.fixture()
def make_signal_trap() -> type[Trap]:
    return Trap


MODULE = TypeVar('MODULE', bound=BaseModule)


class ModuleHarness(Generic[MODULE]):

    def __init__(self, module_class: type[MODULE], config: Config) -> None:
        self._request_list_commands_trap = Trap(_request_list_commands)
        self.auth_message_in_trap = Trap(auth_message_in)
        self.message_out_trap = Trap(message_out)
        self.on_exception_trap = Trap(on_exception)
        self.module_load_trap = Trap(module_load)
        self.module_unload_trap = Trap(module_unload)
        self.config_reload_trap = Trap(config_reload)
        self.config_changed_trap = Trap(config_changed)

        self.module = module_class(config)

    def receive_message_in(self, msg: Message) -> None:
        message_in.send(None, msg=msg)

    def receive_auth_message_in(self, msg: Message, auth: AuthContext) -> None:
        auth_message_in.send(None, msg=msg, auth=auth)

    def send_module_loaded(self, cls: type) -> None:
        module_loaded.send(None, cls=cls)

    def send_module_unloaded(self, cls: type) -> None:
        module_unloaded.send(None, cls=cls)

    def send_config_reloaded(self) -> None:
        config_reloaded.send(None)

    def expect_request_list_commands_signals(self, expected_signals: list[dict[str, Any]]) -> None:
        def wait_condition(trapped: list[dict[str, Any]]) -> None:
            assert trapped == expected_signals
        self._request_list_commands_trap.wait(wait_condition)

    def expect_auth_message_in_signals(self, expected_signals: list[dict[str, Any]]) -> None:
        def wait_condition(trapped: list[dict[str, Any]]) -> None:
            assert trapped == expected_signals
        self.auth_message_in_trap.wait(wait_condition)

    def expect_module_load_signals(self, expected_signals: list[dict[str, Any]]) -> None:
        def wait_condition(trapped: list[dict[str, Any]]) -> None:
            assert trapped == expected_signals
        self.module_load_trap.wait(wait_condition)

    def expect_module_unload_signals(self, expected_signals: list[dict[str, Any]]) -> None:
        def wait_condition(trapped: list[dict[str, Any]]) -> None:
            assert trapped == expected_signals
        self.module_unload_trap.wait(wait_condition)

    def expect_config_reload_signals(self, expected_signals: list[dict[str, Any]]) -> None:
        def wait_condition(trapped: list[dict[str, Any]]) -> None:
            assert trapped == expected_signals
        self.config_reload_trap.wait(wait_condition)

    def expect_message_out_signals(self, expected_signals: list[dict[str, Any]]) -> None:
        def wait_condition(trapped: list[dict[str, Any]]) -> None:
            assert trapped == expected_signals
        self.message_out_trap.wait(wait_condition)

    def expect_config_changed_signals(self, expected_signals: list[dict[str, Any]]) -> None:
        def wait_condition(trapped: list[dict[str, Any]]) -> None:
            assert trapped == expected_signals
        self.config_changed_trap.wait(wait_condition)

    def reset_message_out_signals(self) -> None:
        self.message_out_trap.reset()

    def stop(self) -> None:
        self.module.stop()
        for captured in self.on_exception_trap.trapped:
            e = captured['e']
            raise e


class ModuleHarnessFactory:

    def __init__(self) -> None:
        self._harnesses: list[ModuleHarness[Any]] = []

    def make(self, module_class: type[MODULE], config: Config) -> ModuleHarness[MODULE]:
        harness = ModuleHarness(module_class, config)
        self._harnesses.append(harness)
        return harness

    def _stop_all(self) -> None:
        for harness in self._harnesses:
            harness.stop()


@pytest.fixture()
def module_harness_factory(request: pytest.FixtureRequest) -> ModuleHarnessFactory:
    factory = ModuleHarnessFactory()

    def teardown() -> None:
        factory._stop_all()

    request.addfinalizer(teardown)
    return factory


@pytest.fixture()
def unauthorised_context() -> AuthContext:
    return AuthContext(None, [])


@pytest.fixture()
def admin_context() -> AuthContext:
    return AuthContext(uuid='admin-uuid', groups=['admin'])
