from botnet.config import Config
from botnet.manager import Manager
from botnet.modules.builtin.meta import Meta


def make_config():
    config = {'module_config': {'base_responder': {'command_prefix': '.'}}}
    config = Config(config)
    return config


def test_help(cl, msg_t, make_privmsg, rec_msg):
    """Test help command. Only Meta module should respond to that command
    without any parameters."""
    msg = make_privmsg('.help')
    config = make_config()
    mng = Manager()
    re = Meta(config)

    rec_msg(msg)
    assert msg_t.msg


def test_bots(cl, msg_t, make_privmsg, rec_msg):
    msg = make_privmsg('.bots')
    config = make_config()
    re = Meta(config)

    rec_msg(msg)
    assert msg_t.msg


def test_git(cl, msg_t, make_privmsg, rec_msg):
    msg = make_privmsg('.git')
    config = make_config()
    re = Meta(config)

    rec_msg(msg)
    assert msg_t.msg
