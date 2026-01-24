from botnet.modules.builtin.c3 import C3
from botnet.config import Config
from botnet.message import Message
import datetime
import pytest


def test_help(make_privmsg, make_incoming_privmsg, unauthorised_context, test_c3):
    msg = make_incoming_privmsg('.help', target='#channel')
    assert test_c3.module.get_all_commands(msg, unauthorised_context) == {'help', 'c3'}


def test_c3_command(make_privmsg, make_incoming_privmsg, unauthorised_context, test_c3):
    msg = make_incoming_privmsg('.c3', nick='author', target='#channel')
    test_c3.receive_auth_message_in(msg, unauthorised_context)

    test_c3.expect_message_out_signals([
        {
            'msg': Message.new_from_string('PRIVMSG #channel :Time to 39C3: 26 days')
        }
    ])


@pytest.fixture()
def test_c3(module_harness_factory):
    class TestC3Module(C3):
        def __init__(self, config):
            super().__init__(config)

        def now(self) -> datetime.datetime:
            # Fixed date for testing: Dec 1, 2025 (so next congress is Dec 27, 2025)
            return datetime.datetime(year=2025, month=12, day=1)

    config = Config({})
    return module_harness_factory.make(TestC3Module, config)
