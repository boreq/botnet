from botnet.message import Message
from botnet.signals import message_out, message_in, clear_state
import logging
import os
import pytest
import tempfile


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
def msg_t():
    class Trap(object):
        """Saves the last message sent via the message_out signal."""

        def __init__(self):
            self.msg = None
            message_out.connect(self.on_message_out)

        def on_message_out(self, sender, msg):
            self.msg = msg

        def reset(self):
            self.msg = None

    return Trap()


@pytest.fixture()
def msg_l():
    class LTrap(object):
        """Saves all messages sent via the message_out signal."""

        def __init__(self):
            self.msgs = []
            message_out.connect(self.on_message_out)

        def __repr__(self):
            return '<LTrap: %s>' % self.msgs

        def on_message_out(self, sender, msg):
            self.msgs.append(msg)

        def reset(self):
            self.msgs = []

    return LTrap()


@pytest.fixture()
def make_privmsg():
    """Provides a PRIVMSG message factory."""
    def f(text, nick='nick'):
        text = ':%s!~user@1-2-3-4.example.com PRIVMSG #channel :%s' % (nick, text)
        msg = Message()
        msg.from_string(text)
        return msg
    return f


@pytest.fixture()
def rec_msg():
    """Provides a function used for sending messages via message_in signal."""
    def f(msg):
        message_in.send(None, msg=msg)
    return f


@pytest.fixture()
def send_msg():
    """Provides a function used for sending messages via message_out signal."""
    def f(msg):
        message_out.send(None, msg=msg)
    return f

@pytest.fixture()
def cl():
    clear_state()

