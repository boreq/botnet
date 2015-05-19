import os
from botnet.config import Config
from botnet.modules.builtin.quotes import Quotes
from botnet.message import Message
from botnet.signals import message_in


def test_quotes(msg_t, make_privmsg):
    dirname = os.path.dirname(os.path.realpath(__file__))
    filename = os.path.join(dirname, 'quotes')

    q = Quotes(Config())
    msg = make_privmsg('.lotr')

    message_in.send(None, msg=msg)
    assert not msg_t.msg

    q.config_set('lotr', filename)
    message_in.send(None, msg=msg)
    assert msg_t.msg


def test_quotes_gone(make_privmsg):
    q = Quotes(Config())
    msg = make_privmsg('.gone')

    q.config_set('gone', 'gone')
    message_in.send(None, msg=msg)
