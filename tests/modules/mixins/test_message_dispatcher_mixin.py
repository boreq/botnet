from botnet.config import Config
from botnet.message import Message
from botnet.modules import BaseModule
from botnet.signals import message_in
from botnet.modules.mixins import MessageDispatcherMixin


def make_privmsg(text):
    text = ':nick!~user@1-2-3-4.example.com PRIVMSG %s' % text
    msg = Message()
    msg.from_string(text)
    return msg


class Tester(MessageDispatcherMixin, BaseModule):

    def __init__(self, config):
        super(Tester, self).__init__(config)
        self.launched_main = False
        self.launched_priv = False
        self.launched_command = False

        self.launched_admin_priv = False
        self.launched_admin_command = False

    def get_command_prefix(self):
        return '.'
    
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


def assert_normal(t):
    assert t.launched_main
    assert t.launched_command
    assert t.launched_priv
    assert not t.launched_admin_command
    assert not t.launched_admin_priv


def test_dispatching():
    t = Tester(Config())
    msg = make_privmsg('#channel :.test')
    message_in.send(None, msg=msg)
    assert_normal(t)


def test_dispatching_args():
    msg = make_privmsg('#channel :.test arg1 arg2')
    t = Tester(Config())
    message_in.send(None, msg=msg)
    assert_normal(t)


def test_dispatching_prefix():
    class PrefixTester(Tester):

        def get_command_prefix(self):
            return ':'

    msg = make_privmsg('#channel ::test arg1 arg2')
    t = PrefixTester(Config())
    message_in.send(None, msg=msg)
    assert_normal(t)


def test_admin_dispatching():
    from botnet.modules.builtin.admin import Admin
    from modules.builtin.test_admin import admin_make_message, data4, send_data

    def make_admin_config(command_prefix='.'):
        config = {
            'module_config': {
                'botnet': {
                    'admin': {
                        'admins': [
                            'nick4'
                        ]
                    }
                }
            }
        }
        config = Config(config)
        return config

    admin_config = make_admin_config()

    t = Tester(Config())
    ad = Admin(admin_config)

    msg = make_privmsg('#channel :.test')
    message_in.send(None, msg=msg)
    assert t.launched_main
    assert t.launched_command
    assert t.launched_priv
    assert not t.launched_admin_command
    assert not t.launched_admin_priv

    msg = admin_make_message('nick4', '.test')
    message_in.send(None, msg=msg)
    send_data(data4)
    assert t.launched_admin_command
    assert t.launched_admin_priv
