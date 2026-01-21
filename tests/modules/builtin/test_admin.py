from botnet.config import Config
from botnet.modules.builtin.admin import Admin
from botnet.message import Message
from botnet.signals import message_in


data1 = [
    ':server.example.com 311 target_nick nick1 ~user freebsd/user/username * :real name',
    ':server.example.com 312 target_nick nick1 serv.example.com :Server info',
    ':server.example.com 301 target_nick nick1 :I am away',
    ':server.example.com 319 target_nick nick1 #channel1 #channel2',
    ':server.example.com 318 target_nick nick1 :End of /WHOIS list.',
]

data2 = [
    ':server.example.com 311 target_nick nick2 ~user freebsd/user/username * :real name',
    ':server.example.com 312 target_nick nick2 serv.example.com :Server info',
    ':server.example.com 301 target_nick nick2 :I am away',
    ':server.example.com 319 target_nick nick2 #channel1 #channel2',
    ':server.example.com 318 target_nick nick2 :End of /WHOIS list.',
]

# Rizon auth
data3 = [
    ':server.example.com 311 target_nick nick3 ~user freebsd/user/username * :real name',
    ':server.example.com 312 target_nick nick3 serv.example.com :Server info',
    ':server.example.com 319 target_nick nick3 #channel1 #channel2',
    ':server.example.com 307 target_nick nick3 :has identified for this nick',
    ':server.example.com 318 target_nick nick3 :End of /WHOIS list.',
]

# Freenode auth
data4 = [
    ':server.example.com 311 target_nick nick4 ~user freebsd/user/username * :real name',
    ':server.example.com 312 target_nick nick4 serv.example.com :Server info',
    ':server.example.com 319 target_nick nick4 #channel1 #channel2',
    ':server.example.com 330 target_nick nick4 nick4 :is logged in as',
    ':server.example.com 318 target_nick nick4 :End of /WHOIS list.',
]


def make_config():
    config = {
        'module_config': {
            'botnet': {
                'admin': {}
            }
        }
    }
    return Config(config)


def send_data(data):
    for text in data:
        msg = Message()
        msg.from_string(text)
        message_in.send(None, msg=msg)


def test_whois_single():
    config = make_config()
    a = Admin(config)

    send_data(data1)
    assert not a._whois_current
    d = a._whois_cache.get('nick1')
    assert d
    assert d['nick'] == 'nick1'
    assert d['user'] == '~user'
    assert d['host'] == 'freebsd/user/username'
    assert d['real_name'] == 'real name'
    assert d['channels'] == ['#channel1', '#channel2']
    assert d['server'] == 'serv.example.com'
    assert d['server_info'] == 'Server info'
    assert d['away'] == 'I am away'


def test_whois_dual():
    config = make_config()
    a = Admin(config)

    send_data(data1)
    assert a._whois_cache.get('nick1')
    assert not a._whois_current

    send_data(data2)
    assert a._whois_cache.get('nick1')
    assert a._whois_cache.get('nick2')
    assert not a._whois_current


def test_whois_intertwined():
    config = make_config()
    a = Admin(config)

    for i in range(len(data1)):
        msg = Message()
        msg.from_string(data1[i])
        message_in.send(None, msg=msg)

        msg = Message()
        msg.from_string(data2[i])
        message_in.send(None, msg=msg)

    assert a._whois_cache.get('nick1')
    assert a._whois_cache.get('nick2')
    assert not a._whois_current


def test_defered(msg_t):
    class Tester(object):

        def __init__(self):
            self.data = None

        def on_complete(self, data):
            self.data = data

    config = make_config()
    a = Admin(config)
    t = Tester()

    assert not msg_t.msg
    a.whois_schedule('nick1', t.on_complete)
    assert msg_t.msg # has WhoisMixin requested whois?
    send_data(data1) # fake server answer
    assert t.data    # has WhoisMixin launched the deferred function?


def admin_make_message(nick, text):
    text = ':%s!~user@1-2-3-4.example.com PRIVMSG %s' % (nick, text)
    msg = Message()
    msg.from_string(text)
    return msg


class AdminTrap(object):

    def __init__(self):
        self.msg = None
        admin_message_in.connect(self.on_admin_message_in)

    def on_admin_message_in(self, sender, msg):
        self.msg = msg

    def reset(self):
        self.msg = None


def test_signal_rizon(msg_t):

    config = make_config()
    config['module_config']['botnet']['admin']['admins'] = ['nick3']
    a = Admin(config)
    t = AdminTrap()

    msg = admin_make_message('nick3', 'sth')
    message_in.send(None, msg=msg)
    assert len(a._whois_deferred) == 1
    assert not t.msg
    send_data(data3)
    assert t.msg


def test_signal_freenode(msg_t):

    config = make_config()
    config['module_config']['botnet']['admin']['admins'] = ['nick4']
    a = Admin(config)
    t = AdminTrap()

    msg = admin_make_message('nick4', 'sth')
    message_in.send(None, msg=msg)
    assert len(a._whois_deferred) == 1
    assert not t.msg
    send_data(data4)
    assert t.msg
