import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.modules import AuthContext
from botnet.modules.builtin.anonpost import Anonpost

from ...conftest import MakePrivmsgFixture
from ...conftest import ModuleHarness
from ...conftest import ModuleHarnessFactory


def test_person_anonpost_to_channel(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_anonpost: ModuleHarness[Anonpost]) -> None:
    msg = make_privmsg('.anonpost #channel Hello world!')
    tested_anonpost.receive_auth_message_in(msg, unauthorised_context)

    tested_anonpost.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :ANONPOST: Hello world!')
            },
        ],
    )


def test_admin_anonpost_to_person(make_privmsg: MakePrivmsgFixture, admin_context: AuthContext, tested_anonpost: ModuleHarness[Anonpost]) -> None:
    msg = make_privmsg('.anonpost victim Hello from admin!')
    tested_anonpost.receive_auth_message_in(msg, admin_context)

    tested_anonpost.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG victim :ANONPOST: Hello from admin!')
            },
        ],
    )


def test_admin_anonpost_to_channel(make_privmsg: MakePrivmsgFixture, admin_context: AuthContext, tested_anonpost: ModuleHarness[Anonpost]) -> None:
    msg = make_privmsg('.anonpost #channel Hello from admin!')
    tested_anonpost.receive_auth_message_in(msg, admin_context)

    tested_anonpost.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :ANONPOST: Hello from admin!')
            },
        ],
    )


def test_person_anonpost_to_person_fails(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_anonpost: ModuleHarness[Anonpost]) -> None:
    msg = make_privmsg('.anonpost victim Hello world!')
    tested_anonpost.receive_auth_message_in(msg, unauthorised_context)

    # Should not send any message because unauthorised_context is not an admin
    tested_anonpost.expect_message_out_signals([])


@pytest.fixture()
def tested_anonpost(module_harness_factory: ModuleHarnessFactory) -> ModuleHarness[Anonpost]:
    config = Config(
        {
            'module_config': {
                'botnet': {
                    'anonpost': {}
                },
            },
        }
    )
    return module_harness_factory.make(Anonpost, config)
