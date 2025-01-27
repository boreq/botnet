from botnet.config import Config
from botnet.manager import Manager
from botnet.modules.builtin.countdown import Countdown
from datetime import date


def make_config():
    config = {
        'module_config': {
            'botnet': {
                'countdown':  {
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
    config = Config(config)
    return config


def test_countdown(cl, msg_t, make_privmsg, rec_msg):
    """Test help command. Only Meta module should respond to that command
    without any parameters."""
    msg = make_privmsg('.camp')
    config = make_config()
    mng = Manager()
    re = Countdown(config)

    config['module_config']['countdown'] = {
    }

    rec_msg(msg)
    assert msg_t.msg.to_string() == 'PRIVMSG #channel :It already happened!'


def test_countdown_summary(cl, msg_t, make_privmsg, rec_msg):
    msg = make_privmsg('.summary')
    config = make_config()
    mng = Manager()
    re = Countdown(config)

    #config['module_config']['countdown'] = {
    #}

    rec_msg(msg)
    assert 'camp' in msg_t.msg.to_string()
    assert 'congress' in msg_t.msg.to_string()
