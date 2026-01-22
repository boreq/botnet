import irccodes
from botnet.modules import AuthContext

from botnet.modules.builtin.gatekeep import Gatekeep
from botnet.message import Message
from botnet.config import Config
from botnet.codes import Code
import pytest


def test_pester(make_privmsg, make_incoming_privmsg, unauthorised_context, test_gatekeep) -> None:
    test_gatekeep.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('NAMES #channel')
            },
        ],
    )

    msg = Message(str(Code.RPL_NAMREPLY.value), params=['bot_nick', '@', '#channel', 'nick1 nick2'])
    test_gatekeep.receive_message_in(msg)

    msg = Message(str(Code.RPL_ENDOFNAMES.value), params=['bot_nick', '#channel'])
    test_gatekeep.receive_message_in(msg)

    test_gatekeep.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('NAMES #channel')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person :Skybird, this is Dropkick with a red dash alpha message in two parts. Break. Break. Stand by to copy the list of people who are currently in the channel:')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person :' + irccodes.colored('nick2', 'light red') + ' (0), ' + irccodes.colored('nick1', 'light red') + ' (0)')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person :If you would like to endorse any of them then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'. If you want to see the full report use the \'.gatekeep\' command.')
            },
        ],
    )


def test_endorsement_session(make_privmsg, make_incoming_privmsg, unauthorised_context, test_gatekeep) -> None:
    ctx = AuthContext('person-uuid', ['group'])

    msg = Message(str(Code.RPL_NAMREPLY.value), params=['bot_nick', '@', '#channel', 'nick1 nick2'])
    test_gatekeep.receive_message_in(msg)

    msg = Message(str(Code.RPL_ENDOFNAMES.value), params=['bot_nick', '#channel'])
    test_gatekeep.receive_message_in(msg)

    test_gatekeep.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('NAMES #channel')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person :Skybird, this is Dropkick with a red dash alpha message in two parts. Break. Break. Stand by to copy the list of people who are currently in the channel:')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person :' + irccodes.colored('nick2', 'light red') + ' (0), ' + irccodes.colored('nick1', 'light red') + ' (0)')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person :If you would like to endorse any of them then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'. If you want to see the full report use the \'.gatekeep\' command.')
            },
        ],
    )

    test_gatekeep.reset_message_out_signals()
    msg = make_incoming_privmsg('.gatekeep', target='bot_nick')
    test_gatekeep.receive_auth_message_in(msg, ctx)

    test_gatekeep.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + irccodes.colored('nick2', 'light red') + ' (0), ' + irccodes.colored('nick1', 'light red') + ' (0)')
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :If you would like to endorse anyone then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'.')
            },
        ],
    )

    test_gatekeep.reset_message_out_signals()
    msg = make_incoming_privmsg('.endorse nick1', target='bot_nick')
    test_gatekeep.receive_auth_message_in(msg, ctx)

    test_gatekeep.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :You endorsed nick1!'),
            },
        ],
    )

    test_gatekeep.reset_message_out_signals()
    msg = make_incoming_privmsg('.gatekeep', target='bot_nick')
    test_gatekeep.receive_auth_message_in(msg, ctx)

    test_gatekeep.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + irccodes.colored('nick1', 'green') + ' (1+), ' + irccodes.colored('nick2', 'light red') + ' (0)')
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :If you would like to endorse anyone then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'.')
            },
        ],
    )

    test_gatekeep.reset_message_out_signals()
    msg = make_incoming_privmsg('.endorse nick2', target='bot_nick')
    test_gatekeep.receive_auth_message_in(msg, ctx)

    test_gatekeep.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :You endorsed nick2!'),
            },
        ],
    )

    test_gatekeep.reset_message_out_signals()
    msg = make_incoming_privmsg('.gatekeep', target='bot_nick')
    test_gatekeep.receive_auth_message_in(msg, ctx)

    test_gatekeep.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + irccodes.colored('nick2', 'green') + ' (1+), ' + irccodes.colored('nick1', 'green') + ' (1+)')
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :If you would like to endorse anyone then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'.')
            },
        ],
    )

    test_gatekeep.reset_message_out_signals()
    msg = make_incoming_privmsg('.unendorse nick2', target='bot_nick')
    test_gatekeep.receive_auth_message_in(msg, ctx)

    test_gatekeep.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :You unendorsed nick2!'),
            },
        ],
    )

    test_gatekeep.reset_message_out_signals()
    msg = make_incoming_privmsg('.gatekeep', target='bot_nick')
    test_gatekeep.receive_auth_message_in(msg, ctx)

    test_gatekeep.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + irccodes.colored('nick1', 'green') + ' (1+), ' + irccodes.colored('nick2', 'light red') + ' (0)')
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :If you would like to endorse anyone then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'.')
            },
        ],
    )


@pytest.fixture()
def test_gatekeep(module_harness_factory, tmp_file):
    class TestGatekeep(Gatekeep):
        pass

    with open(tmp_file, 'w') as f:
        f.write('{ "authorised_people_infos": {}, "personas": [], "nick_infos": {} }')

    config = Config(
        {
            'module_config': {
                'botnet': {
                    'auth': {
                        'people': [
                            {
                                'uuid': 'person-uuid',
                                'groups': ['group'],
                                'contact': ['person'],
                            }
                        ]
                    },
                    'gatekeep': {
                        'data': tmp_file,
                        'channel': '#channel',
                        'authorised_group': 'group',
                    }
                },
            },
        }
    )

    return module_harness_factory.make(TestGatekeep, config)
