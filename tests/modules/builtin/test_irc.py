import time
from botnet.config import Config
from botnet.modules.builtin.irc import IRC, InactivityMonitor, Buffer
from botnet import Message


def make_config():
    config = {
        'module_config': {
            'botnet': {
                'irc': {}
            }
        }
    }
    return Config(config)


def test_process_data():
    data = [b'data1\r\n', b'da', b'ta2\r\nda', b'ta3', b'\r\n', b'']
    buf = Buffer()
    lines = []
    for d in data:
        lines.extend(buf.process_data(d))
    assert len(lines) == 3
    assert lines[0] == b'data1'
    assert lines[1] == b'data2'
    assert lines[2] == b'data3'


def test_process_invalid_data():
    msg = bytes.fromhex('3a6e69636b217e7a401f03344a6f796f7573032e03334b77616e7a6161032e1f6e69636b20505249564d534720726f626f746e65745f74657374203a746573740d0a')
    data = [b'data1\r\n', msg, b'da', b'ta2\r\nda', b'ta3', b'\r\n', b'']
    buf = Buffer()
    lines = []
    for d in data:
        lines.extend(buf.process_data(d))
    assert len(lines) == 4


def test_inactivity_monitor():

    class TestMonitor(InactivityMonitor):

        ping_timeout = 0.5
        abort_timeout = 1

        def __init__(self, irc_module):
            super(TestMonitor, self).__init__(irc_module)
            self.pinged = False
            self.aborted = False

        def on_timer_ping(self):
            self.pinged = True

        def on_timer_abort(self):
            self.aborted = True

    config = make_config()
    irc = IRC(config)

    with TestMonitor(irc) as t:
        time.sleep(1.5)
        assert t.pinged
        assert t.aborted

    with TestMonitor(irc) as t:
        time.sleep(.75)
        assert t.pinged
        assert not t.aborted

    with TestMonitor(irc) as t:
        assert not t.pinged
        assert not t.aborted


def test_inactivity_monitor_repeated():
    class TestMonitor(InactivityMonitor):

        ping_timeout = 0.5
        ping_repeat = 0.1
        abort_timeout = 1

        def __init__(self, irc_module):
            super(TestMonitor, self).__init__(irc_module)
            self.pinged = 0
            self.aborted = 0

        def on_timer_ping(self):
            super(TestMonitor, self).on_timer_ping()
            self.pinged += 1

        def on_timer_abort(self):
            super(TestMonitor, self).on_timer_abort()
            self.aborted += 1

    config = make_config()
    irc = IRC(config)

    with TestMonitor(irc) as t:
        time.sleep(1.5)
        assert t.pinged > 3
        assert t.aborted > 0


def test_empty_config():
    config = make_config()
    irc = IRC(config)

    msg = Message()
    msg.from_string(':nick!~user@host.com PRIVMSG #channel :lorem ipsum')
    assert not irc.should_ignore(msg)


def test_ignore():
    ignore_list = [
        "nick!*@*",
        "*!*@example.com",
    ]

    config = make_config()
    config['module_config']['botnet']['irc']['ignore'] = ignore_list

    irc = IRC(config)

    msg = Message()
    msg.from_string(':nick!~user@host.com PRIVMSG #channel :lorem ipsum')
    assert irc.should_ignore(msg)

    msg = Message()
    msg.from_string(':othernick!~user@example.com PRIVMSG #channel :lorem ipsum')
    assert irc.should_ignore(msg)

    msg = Message()
    msg.from_string(':othernick!~user@example.net PRIVMSG #channel :lorem ipsum')
    assert not irc.should_ignore(msg)
