from datetime import datetime

import pytest

from botnet import Message
from botnet.config import Config
from botnet.modules import BaseResponder
from botnet.modules.builtin.irc import IRC
from botnet.modules.builtin.irc import Buffer
from botnet.modules.builtin.irc import InactivityMonitor
from botnet.signals import message_out


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


def test_inactivity_monitor(make_signal_trap):
    class TestMonitor(InactivityMonitor):
        ping_timeout = 0.1
        abort_timeout = 0.2

        def _now(self):
            return datetime.fromtimestamp(123.456)

    class MockRestarter:
        def __init__(self):
            self.restarted = 0

        def restart(self):
            self.restarted += 1

    restarter = MockRestarter()
    trap = make_signal_trap(message_out)

    with TestMonitor(restarter):
        def check_pings(trapped):
            assert trapped == [
                {'msg': Message(command='PING', params=['123.456'])}
            ]
            assert restarter.restarted > 0
        trap.wait(check_pings)

    trap.reset()
    restarter.restarted = 0
    with TestMonitor(restarter):
        def check_pings(trapped):
            assert trapped == [
                {'msg': Message(command='PING', params=['123.456'])}
            ]
            assert restarter.restarted == 0
        trap.wait(check_pings)

    trap.reset()
    restarter.restarted = 0
    with TestMonitor(restarter):
        def check_pings(trapped):
            assert trapped == []
            assert restarter.restarted == 0
        trap.wait(check_pings)


def test_inactivity_monitor_repeated(make_signal_trap):
    class TestMonitor(InactivityMonitor):
        ping_timeout = 0.1
        ping_repeat = 0.05
        abort_timeout = 0.2

        def _now(self):
            return datetime.fromtimestamp(123.456)

    class MockRestarter:
        def __init__(self):
            self.restarted = 0

        def restart(self):
            self.restarted += 1

    restarter = MockRestarter()
    trap = make_signal_trap(message_out)

    with TestMonitor(restarter):
        def check_pings(trapped):
            assert len(trapped) > 2
            for entry in trapped:
                assert entry['msg'] == Message(command='PING', params=['123.456'])
            assert restarter.restarted > 0
        trap.wait(check_pings)


def test_ignore_empty_config(tested_irc):
    irc = tested_irc.module

    msg = Message.new_from_string(':nick!~user@host.com PRIVMSG #channel :lorem ipsum')
    assert not irc.should_ignore(msg)


def test_ignore(tested_irc, irc_config):
    ignore_list = [
        "nick!*@*",
        "*!*@example.com",
    ]

    irc_config['module_config']['botnet']['irc']['ignore'] = ignore_list

    irc = tested_irc.module

    msg = Message.new_from_string(':nick!~user@host.com PRIVMSG #channel :lorem ipsum')
    assert irc.should_ignore(msg)

    msg = Message.new_from_string(':othernick!~user@example.com PRIVMSG #channel :lorem ipsum')
    assert irc.should_ignore(msg)

    msg = Message.new_from_string(':othernick!~user@example.net PRIVMSG #channel :lorem ipsum')
    assert not irc.should_ignore(msg)


@pytest.fixture
def irc_config():
    config = {
        'module_config': {
            'botnet': {
                'irc': {
                    'server': 'irc.example.com',
                    'port': 6667,
                    'ssl': True,
                    'nick': 'testbot',
                    'channels': [
                        {
                            'name': '#example',

                        }
                    ],
                    'ignore': [],
                    'inactivity_monitor': False
                }
            }
        }
    }
    return Config(config)


@pytest.fixture
def tested_irc(module_harness_factory, irc_config):
    class TestedIRC(IRC):
        def start(self):
            pass

        def stop(self):
            super(BaseResponder, self).stop()
            self.stop_event.set()

    return module_harness_factory.make(TestedIRC, irc_config)
