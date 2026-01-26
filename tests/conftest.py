from botnet.config import Config
from botnet.message import Message, IncomingPrivateMessage, Nick, Target, Text
from botnet.modules import AuthContext
from botnet.signals import message_out, message_in, auth_message_in, clear_state, on_exception, \
    _request_list_commands, module_load, module_unload, config_reload, module_loaded, module_unloaded, config_reloaded
import logging
import os
import pytest
import tempfile
import time
from typing import Callable


log_format = '%(asctime)s %(levelname)s %(name)s: %(message)s'
log_level = logging.DEBUG
logging.basicConfig(format=log_format, level=log_level)


@pytest.fixture()
def tmp_file(request):
    fd, path = tempfile.mkstemp()

    def teardown():
        os.close(fd)
        os.remove(path)

    request.addfinalizer(teardown)
    return path


@pytest.fixture()
def make_privmsg():
    """Provides a PRIVMSG message factory."""
    def f(text, nick='nick', target='#channel'):
        return Message(
            prefix='%s!~user@1-2-3-4.example.com' % nick,
            command='PRIVMSG',
            params=[target, text]
        )
    return f


@pytest.fixture()
def make_incoming_privmsg():
    """Provides a PRIVMSG message factory."""
    def f(text, nick='nick', target='#channel'):
        return IncomingPrivateMessage(
            sender=Nick(nick),
            target=Target.new_from_string(target),
            text=Text(text),
        )
    return f


@pytest.fixture()
def rec_msg():
    """Provides a function used for sending messages via message_in signal."""
    def f(msg):
        message_in.send(None, msg=msg)
    return f


@pytest.fixture()
def rec_auth_msg():
    """Provides a function used for sending messages via auth_message_in signal."""
    def f(msg):
        auth_message_in.send(None, msg=msg)
    return f


@pytest.fixture()
def resource_path():
    """Provides a function used for creating paths to resources."""
    def f(path):
        dirpath = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(dirpath, 'resources', path)
    return f


@pytest.fixture()
def clear_signal_state():
    clear_state()


class Trap(object):
    def __init__(self, signal) -> None:
        self.trapped: list[dict] = []
        signal.connect(self.on_signal)

    def on_signal(self, sender, **kwargs) -> None:
        self.trapped.append(kwargs)

    def reset(self) -> None:
        self.trapped = []

    def wait(self, assertion: Callable[[list], None], max_seconds=1) -> None:
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
def make_signal_trap():
    return Trap


class ModuleHarness:

    def __init__(self, module_class, config: Config) -> None:
        self._request_list_commands_trap = Trap(_request_list_commands)
        self.auth_message_in_trap = Trap(auth_message_in)
        self.message_out_trap = Trap(message_out)
        self.on_exception_trap = Trap(on_exception)
        self.module_load_trap = Trap(module_load)
        self.module_unload_trap = Trap(module_unload)
        self.config_reload_trap = Trap(config_reload)

        self.module = module_class(config)

    def receive_message_in(self, msg: Message) -> None:
        message_in.send(None, msg=msg)

    def receive_auth_message_in(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
        auth_message_in.send(None, msg=msg, auth=auth)

    def send_module_loaded(self, cls: type) -> None:
        module_loaded.send(None, cls=cls)

    def send_module_unloaded(self, cls: type) -> None:
        module_unloaded.send(None, cls=cls)

    def send_config_reloaded(self) -> None:
        config_reloaded.send(None)

    def expect_request_list_commands_signals(self, expected_signals: list[dict]) -> None:
        def wait_condition(trapped):
            assert trapped == expected_signals
        self._request_list_commands_trap.wait(wait_condition)

    def expect_auth_message_in_signals(self, expected_signals: list[dict]) -> None:
        def wait_condition(trapped):
            assert trapped == expected_signals
        self.auth_message_in_trap.wait(wait_condition)

    def expect_module_load_signals(self, expected_signals: list[dict]) -> None:
        def wait_condition(trapped):
            assert trapped == expected_signals
        self.module_load_trap.wait(wait_condition)

    def expect_module_unload_signals(self, expected_signals: list[dict]) -> None:
        def wait_condition(trapped):
            assert trapped == expected_signals
        self.module_unload_trap.wait(wait_condition)

    def expect_config_reload_signals(self, expected_signals: list[dict]) -> None:
        def wait_condition(trapped):
            assert trapped == expected_signals
        self.config_reload_trap.wait(wait_condition)

    def expect_message_out_signals(self, expected_signals: list[dict]) -> None:
        def wait_condition(trapped):
            assert trapped == expected_signals
        self.message_out_trap.wait(wait_condition)

    def reset_message_out_signals(self) -> None:
        self.message_out_trap.reset()

    def stop(self) -> None:
        self.module.stop()
        for e in self.on_exception_trap.trapped:
            raise e['e']


class ModuleHarnessFactory:

    def __init__(self) -> None:
        self._harnesses: list[ModuleHarness] = []

    def make(self, module_class: Callable, config: Config) -> ModuleHarness:
        harness = ModuleHarness(module_class, config)
        self._harnesses.append(harness)
        return harness

    def _stop_all(self) -> None:
        for harness in self._harnesses:
            harness.stop()


@pytest.fixture()
def module_harness_factory(request) -> ModuleHarnessFactory:
    factory = ModuleHarnessFactory()

    def teardown():
        factory._stop_all()

    request.addfinalizer(teardown)
    return factory


@pytest.fixture()
def unauthorised_context() -> AuthContext:
    return AuthContext(None, [])


@pytest.fixture()
def admin_context() -> AuthContext:
    return AuthContext(uuid='admin-uuid', groups=['admin'])
