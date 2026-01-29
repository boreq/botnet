import pytest

from botnet.config import Config
from botnet.modules import AuthContext
from botnet.modules.builtin.reactions import Reactions

from ...conftest import MakePrivmsgFixture
from ...conftest import ModuleHarness
from ...conftest import ModuleHarnessFactory


def test_cute(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_reactions: ModuleHarness[Reactions]) -> None:
    msg = make_privmsg('.cute', nick='author', target='#channel')
    tested_reactions.receive_auth_message_in(msg, unauthorised_context)

    assert len(tested_reactions.message_out_trap.trapped) == 1


def test_cute_target(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_reactions: ModuleHarness[Reactions]) -> None:
    msg = make_privmsg('.cute someone', nick='author', target='#channel')
    tested_reactions.receive_auth_message_in(msg, unauthorised_context)

    assert len(tested_reactions.message_out_trap.trapped) == 1
    assert 'someone' in tested_reactions.message_out_trap.trapped[0]['msg'].params[1]


def test_magic(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_reactions: ModuleHarness[Reactions]) -> None:
    msg = make_privmsg('.magic', nick='author', target='#channel')
    tested_reactions.receive_auth_message_in(msg, unauthorised_context)

    assert len(tested_reactions.message_out_trap.trapped) == 1


@pytest.fixture()
def tested_reactions(module_harness_factory: ModuleHarnessFactory, tmp_file: str) -> ModuleHarness[Reactions]:
    return module_harness_factory.make(Reactions, Config())
