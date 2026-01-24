import pytest
from botnet.modules.builtin.reactions import Reactions
from botnet.config import Config


def test_cute(make_privmsg, make_incoming_privmsg, unauthorised_context, test_sed):
    msg = make_incoming_privmsg('.cute', nick='author', target='#channel')
    test_sed.receive_auth_message_in(msg, unauthorised_context)

    assert len(test_sed.message_out_trap.trapped) == 1


def test_cute_target(make_privmsg, make_incoming_privmsg, unauthorised_context, test_sed):
    msg = make_incoming_privmsg('.cute someone', nick='author', target='#channel')
    test_sed.receive_auth_message_in(msg, unauthorised_context)

    assert len(test_sed.message_out_trap.trapped) == 1
    assert 'someone' in test_sed.message_out_trap.trapped[0]['msg'].params[1]


def test_magic(make_privmsg, make_incoming_privmsg, unauthorised_context, test_sed):
    msg = make_incoming_privmsg('.magic', nick='author', target='#channel')
    test_sed.receive_auth_message_in(msg, unauthorised_context)

    assert len(test_sed.message_out_trap.trapped) == 1


@pytest.fixture()
def test_sed(module_harness_factory, tmp_file):
    class TestReactions(Reactions):
        pass

    return module_harness_factory.make(TestReactions, Config())
