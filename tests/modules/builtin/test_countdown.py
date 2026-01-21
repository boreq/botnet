from botnet.config import Config
from botnet.modules.builtin.countdown import Countdown


def make_config():
    config = {
        'module_config': {
            'botnet': {
                'countdown': {
                    'summary_command': 'summary',
                    'commands': {
                        'camp': {
                            'year': 2023,
                            'month': 8,
                            'day': 15,
                        },
                        'congress': {
                            'year': 2025,
                            'month': 8,
                            'day': 15,
                        }
                    }
                }
            }
        }
    }
    return Config(config)


def test_countdown(cl, msg_t, make_privmsg, rec_msg):
    config = make_config()
    re = Countdown(config)

    msg = make_privmsg('.camp')
    rec_msg(msg)
    assert msg_t.msg.to_string() == 'PRIVMSG #channel :It already happened!'

    re.stop()


def test_countdown_summary(cl, msg_t, make_privmsg, rec_msg):
    config = make_config()
    re = Countdown(config)

    msg = make_privmsg('.summary')
    rec_msg(msg)
    assert 'camp' in msg_t.msg.to_string()
    assert 'congress' in msg_t.msg.to_string()

    re.stop()
