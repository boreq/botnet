from botnet.message import Message
from botnet.signals import message_out
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


def test_countdown(make_signal_trap, make_privmsg, rec_msg):
    config = make_config()
    re = Countdown(config)

    message_out_signal_trap = make_signal_trap(message_out)

    msg = make_privmsg('.camp')
    rec_msg(msg)

    def wait_condition(trapped):
        assert trapped == [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :It already happened!')
            }
        ]
    message_out_signal_trap.wait(wait_condition)

    re.stop()


def test_countdown_summary(make_signal_trap, make_privmsg, rec_msg):
    config = make_config()
    re = Countdown(config)

    message_out_signal_trap = make_signal_trap(message_out)

    msg = make_privmsg('.summary')
    rec_msg(msg)

    def wait_condition(trapped):
        assert trapped == [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :camp: It already happened, congress: It already happened')
            }
        ]
    message_out_signal_trap.wait(wait_condition)

    re.stop()
