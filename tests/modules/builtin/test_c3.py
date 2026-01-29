import datetime

import pytest

from botnet.config import Config
from botnet.message import IncomingPrivateMessage
from botnet.message import Message
from botnet.modules import AuthContext
from botnet.modules.builtin.c3 import C3

from ...conftest import MakePrivmsgFixture
from ...conftest import ModuleHarness
from ...conftest import ModuleHarnessFactory


def test_help(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_c3: ModuleHarness[C3]) -> None:
    msg = IncomingPrivateMessage.new_from_message(make_privmsg('.help', target='#channel'))
    assert tested_c3.module.get_all_commands(msg, unauthorised_context) == {'help', 'c3'}


def test_c3_command(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_c3: ModuleHarness[C3]) -> None:
    msg = make_privmsg('.c3', nick='author', target='#channel')
    tested_c3.receive_auth_message_in(msg, unauthorised_context)

    tested_c3.expect_message_out_signals([
        {
            'msg': Message.new_from_string('PRIVMSG #channel :Time to 39C3: 26 days')
        }
    ])


@pytest.fixture()
def tested_c3(module_harness_factory: ModuleHarnessFactory) -> ModuleHarness[C3]:
    class TestedC3(C3):
        def __init__(self, config: Config) -> None:
            super().__init__(config)

        def _now(self) -> datetime.datetime:
            return datetime.datetime(year=2025, month=12, day=1)

    config = Config({})
    return module_harness_factory.make(TestedC3, config)
