import time
from botnet.config import Config
from botnet.modules.builtin.irc import IRC, InactivityMonitor


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
    data = [b'data1\n', b'da', b'ta2\nda', b'ta3', b'\n', b'']
    config = make_config()
    irc = IRC(config)
    lines = []
    for d in data:
        lines.extend(irc.process_data(d))
    assert len(lines) == 3


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
