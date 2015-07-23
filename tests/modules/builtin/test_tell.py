from botnet.config import Config
from botnet.modules.builtin.tell import MessageStore, Tell

def test_message_store(tmp_file):
    ms = MessageStore(lambda: tmp_file)

    a = ms.get_messages('target1')
    assert a == []

    ms.add_message('author', 'target1', 'text1')
    ms.add_message('author', 'target1', 'text2')
    ms.add_message('author', 'target2', 'text')

    a = ms.get_messages('target1')
    assert len(a) == 2

    a = ms.get_messages('target2')
    assert len(a) == 1

def test_duplicate(tmp_file):
    ms = MessageStore(lambda: tmp_file)
    ms.add_message('author', 'target', 'text')
    ms.add_message('author', 'target', 'text')
    assert len(ms._msg_store) == 1

def test_mod(tmp_file, msg_t, make_privmsg, rec_msg):
    class TestTell(Tell):
        default_config = {
            'message_data': tmp_file
        }

    m = TestTell(Config())
    msg = make_privmsg('.tell target message text', nick='author')
    rec_msg(msg)
    assert 'Will do' in str(msg_t.msg)

    msg = make_privmsg('sth', nick='target')
    rec_msg(msg)
    assert 'message text' in str(msg_t.msg)
