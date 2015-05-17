from botnet.config import Config
from botnet.message import Message
from botnet.modules import BaseResponder, parse_command
from botnet.signals import message_in, message_out


def make_message(text):
    text = ':nick!~user@1-2-3-4.example.com PRIVMSG %s' % text
    msg = Message()
    msg.from_string(text)
    return msg


def make_config(command_prefix='.'):
    config = {'module_config': {'botnet': {'base_responder': {'command_prefix': command_prefix}}}}
    config = Config(config)
    return config


class TestResponder(BaseResponder):

    def __init__(self, config):
        super(TestResponder, self).__init__(config)
        self.launched_main = False
        self.launched_priv = False
        self.launched_admin_priv = False
        self.launched_command = False
        self.launched_admin_command = False

    def command_test(self, msg):
        self.launched_command = True

    def admin_command_test(self, msg):
        self.launched_admin_command = True

    def handle_privmsg(self, msg):
        self.launched_priv = True

    def handle_admin_privmsg(self, msg):
        self.launched_admin_priv = True

    def handle_msg(self, msg):
        self.launched_main = True


def test_dispatching():
    """Test if a responder properly dispatches a message."""

    config = make_config()

    re = TestResponder(config)
    msg = make_message('#channel :.test')
    message_in.send(None, msg=msg)
    assert re.launched_main
    assert re.launched_command
    assert re.launched_priv
    assert not re.launched_admin_command
    assert not re.launched_admin_priv

    msg = make_message('#channel :.test arg1 arg2')
    re = TestResponder(config)
    message_in.send(None, msg=msg)
    assert re.launched_main
    assert re.launched_command
    assert re.launched_priv
    assert not re.launched_admin_command
    assert not re.launched_admin_priv

    config = make_config(':')
    msg = make_message('#channel ::test arg1 arg2')
    re = TestResponder(config)
    message_in.send(None, msg=msg)
    assert re.launched_main
    assert re.launched_command
    assert re.launched_priv
    assert not re.launched_admin_command
    assert not re.launched_admin_priv


def test_help(msg_t):
    """Test help command. Only Meta module should respond to that command
    without any parameters."""
    msg = make_message('#channel :.help')
    config = make_config()

    re = BaseResponder(config)
    message_in.send(None, msg=msg)

    assert not msg_t.msg


def test_specific(msg_t):
    """Test help regarding a specific command."""

    class Responder(BaseResponder):

        def command_test(self, msg):
            pass

    msg = make_message('#channel :.help test')
    config = make_config()

    re = Responder(config)
    message_in.send(None, msg=msg)

    assert msg_t.msg


def test_respond(msg_t):
    """Test if BaseResponder.respond sends messages to proper targets."""
    params = (
        ('#channel :test message', '#channel', False),
        ('bot_nick :test message', 'nick', False),
        ('#channel :test message', 'nick', True),
        ('bot_nick :test message', 'nick', True),
    )
    config = make_config()
    re = BaseResponder(config)

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

    config = make_config()
    msg = make_message('#channel :.test awesome one two three')
    re = TestResponder(config)
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

    config = make_config()
    msg = make_message('#channel :.test')
    re = TestResponder(config)
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

    config = make_config()
    msg = make_message('#channel :.test')
    re = TestResponder(config)
    message_in.send(None, msg=msg)

    assert re.args is not None


def test_is_command():
    config = make_config()
    re = BaseResponder(config)

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
