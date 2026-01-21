from botnet.message import Message
from botnet.signals import message_out, message_in, auth_message_in, clear_state
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
        text = ':%s!~user@1-2-3-4.example.com PRIVMSG %s :%s' % (nick, target, text)
        return Message.new_from_string(text)
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
def send_msg():
    """Provides a function used for sending messages via message_out signal."""
    def f(msg):
        message_out.send(None, msg=msg)
    return f


@pytest.fixture()
def resource_path():
    """Provides a function used for creating paths to resources."""
    def f(path):
        dirpath = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(dirpath, 'resources', path)
    return f


@pytest.fixture()
def clear():
    clear_state()


class Trap(object):
    def __init__(self, signal):
        self.trapped = []
        signal.connect(self.on_signal)

    def on_signal(self, sender, **kwargs):
        self.trapped.append(kwargs)

    def reset(self):
        self.trapped = []

    def wait(self, assertion: Callable[[list], None], max_seconds=2):
        for i in range(max_seconds):
            try:
                assertion(self.trapped)
            except AssertionError:
                time.sleep(1)
                continue
            return
        assertion(self.trapped)


@pytest.fixture()
def make_signal_trap():
    return Trap
