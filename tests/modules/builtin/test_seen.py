from datetime import datetime, timezone
from botnet.message import Message
from botnet.config import Config
from botnet.modules.builtin.seen import Seen
import pytest


def test_seen_sequence(make_privmsg, make_incoming_privmsg, unauthorised_context, test_seen):
    m = test_seen

    msg = make_incoming_privmsg('.seen someone', nick='author', target='#channel')
    m.receive_auth_message_in(msg, unauthorised_context)
    m.expect_message_out_signals([
        {'msg': Message.new_from_string("PRIVMSG #channel :I've never seen someone")}
    ])

    msg = make_privmsg('hello', nick='someone', target='#channel')
    m.receive_message_in(msg)

    msg = make_incoming_privmsg('.seen someone', nick='author', target='#channel')
    m.receive_auth_message_in(msg, unauthorised_context)
    m.expect_message_out_signals([
        {'msg': Message.new_from_string("PRIVMSG #channel :I've never seen someone")},
        {'msg': Message.new_from_string('PRIVMSG #channel :someone was last seen on 2026-01-02 11:12Z')}
    ])


@pytest.fixture()
def test_seen(module_harness_factory, tmp_file):
    class TestSeen(Seen):
        def now(self) -> datetime:
            return datetime(2026, 1, 2, 11, 12, 13, tzinfo=timezone.utc)

    config = {
        'module_config': {
            'botnet': {
                'seen': {
                    'message_data': tmp_file
                }
            }
        }
    }

    return module_harness_factory.make(TestSeen, Config(config))
