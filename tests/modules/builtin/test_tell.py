from datetime import datetime, timezone
from botnet.message import Message
from botnet.config import Config
from botnet.modules.builtin.tell import Tell
import pytest


def test_multiple_messages_for_multiple_users(make_privmsg, make_incoming_privmsg, unauthorised_context, test_tell):
    msg = make_incoming_privmsg('.tell target1 message1', nick='author', target='#channel')
    test_tell.receive_auth_message_in(msg, unauthorised_context)

    msg = make_incoming_privmsg('.tell target1 message2', nick='author', target='#channel')
    test_tell.receive_auth_message_in(msg, unauthorised_context)

    msg = make_incoming_privmsg('.tell target2 message1', nick='author', target='#channel')
    test_tell.receive_auth_message_in(msg, unauthorised_context)

    msg = make_incoming_privmsg('.tell target2 message2', nick='author', target='#channel')
    test_tell.receive_auth_message_in(msg, unauthorised_context)

    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
        ]
    )

    msg = make_privmsg('sth', nick='target1', target='#channel')
    test_tell.receive_message_in(msg)
    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :target1: 2026-01-02 11:12:13Z <author> message1')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :target1: 2026-01-02 11:12:13Z <author> message2')
            },
        ]
    )

    msg = make_privmsg('sth', nick='target2', target='#channel')
    test_tell.receive_message_in(msg)
    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :target1: 2026-01-02 11:12:13Z <author> message1')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :target1: 2026-01-02 11:12:13Z <author> message2')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :target2: 2026-01-02 11:12:13Z <author> message1')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :target2: 2026-01-02 11:12:13Z <author> message2')
            },
        ]
    )


def test_duplicate_messages_are_ignored(make_privmsg, make_incoming_privmsg, unauthorised_context, test_tell):
    msg = make_incoming_privmsg('.tell target message', nick='author', target='#channel')

    test_tell.receive_auth_message_in(msg, unauthorised_context)
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
                'msg': Message.new_from_string('PRIVMSG #channel :target: 2026-01-02 11:12:13Z <author> message')
            },
        ]
    )


def test_messages_arrive_in_the_same_order_they_were_sent(make_privmsg, make_incoming_privmsg, unauthorised_context, test_tell):
    msg = make_incoming_privmsg('.tell target message1', nick='author', target='#channel')
    test_tell.receive_auth_message_in(msg, unauthorised_context)

    msg = make_incoming_privmsg('.tell target message2', nick='author', target='#channel')
    test_tell.receive_auth_message_in(msg, unauthorised_context)

    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
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
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :target: 2026-01-02 11:12:13Z <author> message1')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :target: 2026-01-02 11:12:13Z <author> message2')
            },
        ]
    )


def test_channel_is_case_insensitive(make_privmsg, make_incoming_privmsg, unauthorised_context, test_tell):
    msg = make_incoming_privmsg('.tell target message text', nick='author', target='#channel')
    test_tell.receive_auth_message_in(msg, unauthorised_context)
    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            }
        ]
    )

    msg = make_privmsg('sth', nick='target', target='#chAnnel')
    test_tell.receive_message_in(msg)
    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #chAnnel :target: 2026-01-02 11:12:13Z <author> message text')
            }
        ]
    )


def test_target_is_case_insensitive(make_privmsg, make_incoming_privmsg, unauthorised_context, test_tell):
    msg = make_incoming_privmsg('.tell target message text', nick='author', target='#channel')
    test_tell.receive_auth_message_in(msg, unauthorised_context)
    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            }
        ]
    )

    msg = make_privmsg('sth', nick='tArget', target='#channel')
    test_tell.receive_message_in(msg)
    test_tell.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Will do!')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :tArget: 2026-01-02 11:12:13Z <author> message text')
            }
        ]
    )


def test_same_channel(make_privmsg, make_incoming_privmsg, unauthorised_context, test_tell):
    msg = make_incoming_privmsg('.tell target message text', nick='author', target='#channel')
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
                'msg': Message.new_from_string('PRIVMSG #channel :target: 2026-01-02 11:12:13Z <author> message text')
            }
        ]
    )


def test_other_channel(make_privmsg, make_incoming_privmsg, unauthorised_context, test_tell):
    msg = make_incoming_privmsg('.tell target message text', nick='author', target='#channel')
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


def test_priv(make_privmsg, make_incoming_privmsg, unauthorised_context, test_tell) -> None:
    msg = make_incoming_privmsg('.tell target message text', nick='author', target='bot')
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
                'msg': Message.new_from_string('PRIVMSG target :target: 2026-01-02 11:12:13Z <author> message text')
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
