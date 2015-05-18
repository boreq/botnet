from botnet.config import Config
from botnet.message import Message
from botnet.manager import Manager
from botnet.modules.builtin.meta import Meta
from botnet.signals import message_in, message_out


def make_message(text):
    text = ':nick!~user@1-2-3-4.example.com PRIVMSG %s' % text
    msg = Message()
    msg.from_string(text)
    return msg


def make_config():
    config = {'module_config': {'base_responder': {'command_prefix': '.'}}}
    config = Config(config)
    return config


def test_help(msg_t):
    """Test help command. Only Meta module should respond to that command
    without any parameters."""
    msg = make_message('#channel :.help')
    config = make_config()

    mng = Manager()
    re = Meta(config)
    message_in.send(None, msg=msg)

    assert msg_t.msg


def test_bots(msg_t):
    """Test help command. Only Meta module should respond to that command
    without any parameters."""
    msg = make_message('#channel :.bots')
    config = make_config()

    re = Meta(config)
    message_in.send(None, msg=msg)

    assert msg_t.msg
