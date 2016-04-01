from botnet.config import Config
from botnet.message import Message
from botnet.modules import BaseResponder
from botnet.modules.lib import parse_command
from botnet.modules.builtin.admin import Admin
from botnet.signals import message_in, admin_message_in


def make_message(text):
    text = ':nick!~user@1-2-3-4.example.com PRIVMSG %s' % text
    msg = Message()
    msg.from_string(text)
    return msg


def test_help(msg_t):
    """Test help command. Only Meta module should respond to that command
    without any parameters."""
    msg = make_message('#channel :.help')

    re = BaseResponder(Config())
    message_in.send(None, msg=msg)

    assert not msg_t.msg


def test_specific(msg_l):
    """Test help regarding a specific command."""

    class Responder(BaseResponder):

        def command_test(self, msg):
            pass

        def admin_command_test(self, msg):
            pass

    msg = make_message('#channel :.help test')

    re = Responder(Config())

    message_in.send(None, msg=msg)
    assert len(msg_l.msgs) == 1

    message_in.send(None, msg=msg)
    assert len(msg_l.msgs) == 2


def test_respond(msg_t):
    """Test if BaseResponder.respond sends messages to proper targets."""
    params = (
        ('#channel :test message', '#channel', False),
        ('bot_nick :test message', 'nick', False),
        ('#channel :test message', 'nick', True),
        ('bot_nick :test message', 'nick', True),
    )
    re = BaseResponder(Config())

    for text, target, pm in params:
        msg_t.reset()
        msg = make_message(text)
        re.respond(msg, 'response', pm=pm)
        assert msg_t.msg.params[0] == target


def test_decorator():
    class TestResponder(BaseResponder):

        def __init__(self, config):
            super(TestResponder, self).__init__(config)
            self.args = None

        @parse_command([('test_type', 1), ('something', '+')])
        def command_test(self, msg, args):
            self.args = args

    msg = make_message('#channel :.test awesome one two three')
    re = TestResponder(Config())
    message_in.send(None, msg=msg)

    assert re.args.command == ['.test']
    assert re.args.test_type == ['awesome']
    assert re.args.something == ['one', 'two', 'three']


def test_decorator_dont_launch():
    class TestResponder(BaseResponder):

        def __init__(self, config):
            super(TestResponder, self).__init__(config)
            self.args = None

        @parse_command([('test_type', 1), ('something', '+')], launch_invalid=False)
        def command_test(self, msg, args):
            self.args = True

    msg = make_message('#channel :.test')
    re = TestResponder(Config())
    message_in.send(None, msg=msg)

    assert re.args is None


def test_decorator_launch():
    class TestResponder(BaseResponder):

        def __init__(self, config):
            super(TestResponder, self).__init__(config)
            self.args = None

        @parse_command([('test_type', 1), ('something', '+')], launch_invalid=True)
        def command_test(self, msg, args):
            self.args = True

    msg = make_message('#channel :.test')
    re = TestResponder(Config())
    message_in.send(None, msg=msg)

    assert re.args is not None


def test_is_command():
    re = BaseResponder(Config())

    msg = make_message('#channel :.test')
    assert re.is_command(msg)

    msg = make_message('#channel :.test arg1 arg2')
    assert re.is_command(msg)

    msg = make_message('#channel :.test arg1 arg2')
    assert re.is_command(msg, 'test')

    msg = make_message('#channel :.testing arg1 arg2')
    assert re.is_command(msg, 'testing')
    assert not re.is_command(msg, 'test')

    msg = make_message('#channel :.testing')
    assert re.is_command(msg, 'testing')
    assert not re.is_command(msg, 'test')

    msg = make_message('#channel :.')
    assert not re.is_command(msg, 'test')

    msg = make_message('#channel ::test')
    assert re.is_command(msg, 'test', ':')
    assert re.is_command(msg, 'test', command_prefix=':')
    assert not re.is_command(msg, 'test')

    msg = make_message('#channel : ')
    assert not re.is_command(msg, 'test')
