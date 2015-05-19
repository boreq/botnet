"""
    Tests which check if the examples are correct.
"""

import pytest
from botnet.message import Message
from botnet.signals import message_out, message_in

from botnet.config import Config
from simple_module import SimpleModule 


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


def test_simple_module(msg_t, make_privmsg, rec_msg):
    re = SimpleModule(Config())

    msg = make_privmsg('.respond')
    rec_msg(msg)
    assert 'Responding' in str(msg_t.msg)

    msg = make_privmsg('.hi')
    rec_msg(msg)
    assert 'Hello' in str(msg_t.msg)

    msg = make_privmsg('.say text')
    rec_msg(msg)
    assert 'told me to ' in str(msg_t.msg)

    msg = make_privmsg('.say')
    rec_msg(msg)
    assert 'forgot' in str(msg_t.msg)
