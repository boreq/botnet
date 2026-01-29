import pytest

from botnet.config import Config
from botnet.message import IncomingPrivateMessage
from botnet.message import Message
from botnet.modules import AuthContext
from botnet.modules.builtin.meta import Meta

from ...conftest import MakePrivmsgFixture
from ...conftest import ModuleHarness
from ...conftest import ModuleHarnessFactory


def test_help(unauthorised_context: AuthContext, make_privmsg: MakePrivmsgFixture, tested_meta: ModuleHarness[Meta]) -> None:
    m = tested_meta

    msg = make_privmsg(':help')
    m.receive_auth_message_in(msg, unauthorised_context)
    m.expect_request_list_commands_signals(
        [
            {
                'msg': IncomingPrivateMessage.new_from_message(msg),
                'auth': unauthorised_context,
            }
        ]
    )


def test_bots(unauthorised_context: AuthContext, make_privmsg: MakePrivmsgFixture, tested_meta: ModuleHarness[Meta]) -> None:
    m = tested_meta

    m.receive_message_in(make_privmsg('.bots'))
    m.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Reporting in! [Python] https://github.com/boreq/botnet try :help (https://ibip.0x46.net/)')
            }
        ]
    )


def test_git(unauthorised_context: AuthContext, make_privmsg: MakePrivmsgFixture, tested_meta: ModuleHarness[Meta]) -> None:
    m = tested_meta

    m.receive_auth_message_in(make_privmsg(':git'), unauthorised_context)
    m.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Reporting in! [Python] https://github.com/boreq/botnet try :help (https://ibip.0x46.net/)')
            }
        ]
    )


@pytest.fixture()
def tested_meta(module_harness_factory: ModuleHarnessFactory) -> ModuleHarness[Meta]:
    config = {'module_config': {'botnet': {'base_responder': {'command_prefix': ':'}}}}
    return module_harness_factory.make(Meta, Config(config))
