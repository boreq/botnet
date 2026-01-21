from datetime import datetime, timezone
from botnet.message import Message
from botnet.config import Config
from botnet.modules.builtin.tell import MessageStore, Tell
import pytest


def test_message_store(tmp_file):
    ms = MessageStore(lambda: tmp_file)

    a = ms.get_channel_messages('target1', '#channel')
    assert a == []

    ms.add_message('author', 'target1', 'text1', '#channel', datetime.now())
    ms.add_message('author', 'target1', 'text2', '#channel', datetime.now())
    ms.add_message('author', 'target2', 'text', '#channel', datetime.now())

    a = ms.get_channel_messages('target1', '#channel')
    assert len(a) == 2

    a = ms.get_channel_messages('target2', '#channel')
    assert len(a) == 1


def test_message_store_case_insensitive(tmp_file):
    ms = MessageStore(lambda: tmp_file)

    a = ms.get_channel_messages('target1', '#channel')
    assert a == []

    ms.add_message('author', 'tArget1', 'text1', '#channel', datetime.now())
    ms.add_message('author', 'taRget1', 'text2', '#channel', datetime.now())

    a = ms.get_channel_messages('TaRget1', '#channel')
    assert len(a) == 2


def test_duplicate(tmp_file):
    ms = MessageStore(lambda: tmp_file)
    ms.add_message('author', 'target', 'text', '#channel', datetime.now())
    ms.add_message('author', 'target', 'text', '#channel', datetime.now())
    assert len(ms._msg_store) == 1


def test_message_store_ordering(tmp_file):
    ms = MessageStore(lambda: tmp_file)

    a = ms.get_channel_messages('target1', '#channel')
    assert a == []

    ms.add_message('author', 'target1', 'text1', '#channel', datetime.now())
    ms.add_message('author', 'target1', 'text2', '#channel', datetime.now())

    a = ms.get_channel_messages('target1', '#channel')
    assert len(a) == 2
    assert a[0]['message'] == 'text1'
    assert a[1]['message'] == 'text2'


def test_same_channel(make_privmsg, unauthorised_context, test_tell):
    msg = make_privmsg('.tell target message text', nick='author', target='#channel')
    test_tell.receive_auth_message_in(msg, unauthorised_context)
    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            }
        ]
    )

    msg = make_privmsg('sth', nick='target', target='#channel')
    test_tell.receive_message_in(msg)
    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :target: 2026-01-02 11:12:13 UTC <author> message text')
            }
        ]
    )


def test_other_channel(make_privmsg, unauthorised_context, test_tell):
    msg = make_privmsg('.tell target message text', nick='author', target='#channel')
    test_tell.receive_auth_message_in(msg, unauthorised_context)
    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            }
        ]
    )

    msg = make_privmsg('sth', nick='target', target='#otherchannel')
    test_tell.receive_message_in(msg)
    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            }
        ]
    )


def test_priv(make_privmsg, unauthorised_context, test_tell):
    msg = make_privmsg('.tell target message text', nick='author', target='bot')
    test_tell.receive_auth_message_in(msg, unauthorised_context)
    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG author :Will do!')
            }
        ]
    )

    msg = make_privmsg('message in public channel', nick='target', target='#channel')
    test_tell.receive_message_in(msg)
    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG author :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG target :target: 2026-01-02 11:12:13 UTC <author> message text')
            }
        ]
    )


@pytest.fixture()
def test_tell(module_harness_factory, tmp_file):
    class TestTell(Tell):

        def __init__(self, *args, **kwargs):
            self.default_config = {
                'message_data': tmp_file
            }
            super().__init__(*args, **kwargs)

        def now(self) -> datetime:
            return datetime(2026, 1, 2, 11, 12, 13, tzinfo=timezone.utc)

    return module_harness_factory.make(TestTell, Config())
