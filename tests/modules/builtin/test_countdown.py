import pytest
from botnet.message import Message
from botnet.config import Config
from botnet.modules.builtin.countdown import Countdown
from datetime import date


def make_config():
    config = {
        'module_config': {
            'botnet': {
                'countdown': {
                    'summary_command': 'summary',
                    'commands': [
                        {
                            'names': ['camp'],
                            'year': 2023,
                            'month': 8,
                            'day': 15,
                        },
                        {
                            'names': ['congress'],
                            'year': 2025,
                            'month': 8,
                            'day': 15,
                        }
                    ]
                }
            }
        }
    }
    return Config(config)


def test_camp(make_privmsg, countdown):
    countdown.receive_message_in(make_privmsg('.camp'))
    countdown.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :It already happened!')
            }
        ]
    )


def test_congress(make_privmsg, countdown):
    countdown.receive_message_in(make_privmsg('.congress'))
    countdown.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :14 days left!')
            }
        ]
    )


def test_countdown_summary(make_privmsg, countdown):
    countdown.receive_message_in(make_privmsg('.summary'))
    countdown.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :camp: It already happened, congress: 14 days left')
            }
        ]
    )


@pytest.fixture()
def countdown(module_harness_factory):
    class TestCountdown(Countdown):
        def now(self):
            return date(2025, 8, 1)

    m = module_harness_factory.make(TestCountdown, make_config())
    return m
