from botnet.config import Config
from botnet.modules.builtin.tell import MessageStore, Tell
import pytest


def test_message_store(tmp_file):
    ms = MessageStore(lambda: tmp_file)

    a = ms.get_channel_messages('target1', '#channel')
    assert a == []

    ms.add_message('author', 'target1', 'text1', '#channel')
    ms.add_message('author', 'target1', 'text2', '#channel')
    ms.add_message('author', 'target2', 'text', '#channel')

    a = ms.get_channel_messages('target1', '#channel')
    assert len(a) == 2

    a = ms.get_channel_messages('target2', '#channel')
    assert len(a) == 1


def test_message_store_case_insensitive(tmp_file):
    ms = MessageStore(lambda: tmp_file)

    a = ms.get_channel_messages('target1', '#channel')
    assert a == []

    ms.add_message('author', 'tArget1', 'text1', '#channel')
    ms.add_message('author', 'taRget1', 'text2', '#channel')

    a = ms.get_channel_messages('TaRget1', '#channel')
    assert len(a) == 2


def test_duplicate(tmp_file):
    ms = MessageStore(lambda: tmp_file)
    ms.add_message('author', 'target', 'text', '#channel')
    ms.add_message('author', 'target', 'text', '#channel')
    assert len(ms._msg_store) == 1


def test_message_store_ordering(tmp_file):
    ms = MessageStore(lambda: tmp_file)

    a = ms.get_channel_messages('target1', '#channel')
    assert a == []

    ms.add_message('author', 'target1', 'text1', '#channel')
    ms.add_message('author', 'target1', 'text2', '#channel')

    a = ms.get_channel_messages('target1', '#channel')
    assert len(a) == 2
    assert a[0]['message'] == 'text1'
    assert a[1]['message'] == 'text2'


class TestTell(Tell):

    def __init__(self, tmp_file, *args, **kwargs):
        self.default_config = {
            'message_data': tmp_file
        }
        super().__init__(*args, **kwargs)


def test_same_channel(tmp_file, msg_t, make_privmsg, rec_msg, test_tell):
    msg = make_privmsg('.tell target message text', nick='author', target='#channel')
    rec_msg(msg)

    assert 'Will do' in str(msg_t.msg)

    msg = make_privmsg('sth', nick='target', target='#channel')
    rec_msg(msg)

    assert 'message text' in str(msg_t.msg)


def test_other_channel(tmp_file, msg_t, make_privmsg, rec_msg, test_tell):
    msg = make_privmsg('.tell target message text', nick='author', target='#channel')
    rec_msg(msg)

    assert 'Will do' in str(msg_t.msg)
    msg_t.reset()

    msg = make_privmsg('sth', nick='target', target='#otherchannel')
    rec_msg(msg)

    assert msg_t.msg is None


def test_priv(tmp_file, msg_t, make_privmsg, rec_msg, test_tell):
    msg = make_privmsg('.tell target message text', nick='author', target='bot')
    rec_msg(msg)

    assert 'Will do' in str(msg_t.msg)
    msg_t.reset()

    msg = make_privmsg('message in public channel', nick='target', target='#channel')
    rec_msg(msg)

    assert 'message text' in str(msg_t.msg)
    assert 'target' == msg_t.msg.params[0]


@pytest.fixture()
def test_tell(request, tmp_file):
    m = TestTell(tmp_file, Config())

    def teardown():
        m.stop()

    request.addfinalizer(teardown)
    return m
