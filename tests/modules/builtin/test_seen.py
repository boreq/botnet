from datetime import datetime
from datetime import timezone

import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.modules import AuthContext
from botnet.modules.builtin.seen import Seen

from ...conftest import MakePrivmsgFixture
from ...conftest import ModuleHarness
from ...conftest import ModuleHarnessFactory


def test_seen_sequence(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_seen: ModuleHarness[Seen]) -> None:
    m = tested_seen

    msg = make_privmsg('.seen someone', nick='author', target='#channel')
    m.receive_auth_message_in(msg, unauthorised_context)
    m.expect_message_out_signals([
        {'msg': Message.new_from_string("PRIVMSG #channel :I've never seen someone")}
    ])

    msg = make_privmsg('hello', nick='someone', target='#channel')
    m.receive_message_in(msg)

    msg = make_privmsg('.seen someone', nick='author', target='#channel')
    m.receive_auth_message_in(msg, unauthorised_context)
    m.expect_message_out_signals([
        {'msg': Message.new_from_string("PRIVMSG #channel :I've never seen someone")},
        {'msg': Message.new_from_string('PRIVMSG #channel :someone was last seen on 2026-01-02 11:12Z')}
    ])


@pytest.fixture()
def tested_seen(module_harness_factory: ModuleHarnessFactory, tmp_file: str) -> ModuleHarness[Seen]:
    with open(tmp_file, 'w', encoding='utf-8') as f:
        f.write('{}')

    class TestedSeen(Seen):
        def _now(self) -> datetime:
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

    return module_harness_factory.make(TestedSeen, Config(config))
