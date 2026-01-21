from botnet.config import Config
from botnet.modules.builtin.meta import Meta


def make_config():
    config = {'module_config': {'base_responder': {'command_prefix': '.'}}}
    return Config(config)


def test_help(cl, msg_t, make_privmsg, rec_msg):
    config = make_config()
    re = Meta(config)

    msg = make_privmsg('.help')
    rec_msg(msg)
    assert msg_t.msg

    re.stop()


def test_bots(cl, msg_t, make_privmsg, rec_msg):
    config = make_config()
    re = Meta(config)

    msg = make_privmsg('.bots')
    rec_msg(msg)
    assert msg_t.msg

    re.stop()


def test_git(cl, msg_t, make_privmsg, rec_msg):
    config = make_config()
    re = Meta(config)

    msg = make_privmsg('.git')
    rec_msg(msg)
    assert msg_t.msg

    re.stop()
