from botnet.config import Config
from botnet.modules.irc import IRC


def make_config():
    config = {
        'module_config': {
            'irc': {}
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
