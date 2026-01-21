from botnet.message import Message
from botnet.config import Config
from botnet.modules.builtin.countdown import Countdown


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


def test_countdown(module_harness_factory, make_privmsg):
    m = module_harness_factory.make(Countdown, make_config())

    m.receive_message_in(make_privmsg('.camp'))
    m.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :It already happened!')
            }
        ]
    )


def test_countdown_summary(module_harness_factory, make_privmsg):
    m = module_harness_factory.make(Countdown, make_config())

    m.receive_message_in(make_privmsg('.summary'))
    m.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :camp: It already happened, congress: It already happened')
            }
        ]
    )
