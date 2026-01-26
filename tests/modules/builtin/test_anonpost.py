import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.modules.builtin.anonpost import Anonpost


def test_person_anonpost_to_channel(make_incoming_privmsg, unauthorised_context, test_anonpost) -> None:
    msg = make_incoming_privmsg('.anonpost #channel Hello world!')
    test_anonpost.receive_auth_message_in(msg, unauthorised_context)

    test_anonpost.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :ANONPOST: Hello world!')
            },
        ],
    )


def test_admin_anonpost_to_person(make_incoming_privmsg, admin_context, test_anonpost) -> None:
    msg = make_incoming_privmsg('.anonpost victim Hello from admin!')
    test_anonpost.receive_auth_message_in(msg, admin_context)

    test_anonpost.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG victim :ANONPOST: Hello from admin!')
            },
        ],
    )


def test_admin_anonpost_to_channel(make_incoming_privmsg, admin_context, test_anonpost) -> None:
    msg = make_incoming_privmsg('.anonpost #channel Hello from admin!')
    test_anonpost.receive_auth_message_in(msg, admin_context)

    test_anonpost.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :ANONPOST: Hello from admin!')
            },
        ],
    )


def test_person_anonpost_to_person_fails(make_incoming_privmsg, unauthorised_context, test_anonpost) -> None:
    msg = make_incoming_privmsg('.anonpost victim Hello world!')
    test_anonpost.receive_auth_message_in(msg, unauthorised_context)

    # Should not send any message because unauthorised_context is not an admin
    test_anonpost.expect_message_out_signals([])


@pytest.fixture()
def test_anonpost(module_harness_factory):
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
