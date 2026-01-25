from botnet.modules import AuthContext
from botnet.modules.builtin.vibecheck import Vibecheck
from botnet.modules.lib import colored, Color
from botnet.message import Message
from botnet.config import Config
from botnet.codes import Code
import pytest


def test_pester(make_privmsg, make_incoming_privmsg, unauthorised_context, tested_vibecheck) -> None:
    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('NAMES #channel')
            },
        ],
    )

    msg = Message(str(Code.RPL_NAMREPLY.value), params=['bot_nick', '@', '#channel', 'nick1 nick2'])
    tested_vibecheck.receive_message_in(msg)

    msg = Message(str(Code.RPL_ENDOFNAMES.value), params=['bot_nick', '#channel'])
    tested_vibecheck.receive_message_in(msg)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('NAMES #channel')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person1 :Skybird, this is Dropkick with a red dash alpha message in two parts. Break. Break. Stand by to copy the list of people who are currently in the channel:')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person1 :' + colored('nick2', Color.RED) + ' (?), ' + colored('nick1', Color.RED) + ' (?)'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG person1 :If you would like to endorse any of them then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'. If you want to see the full report use the \'.vibecheck\' command.')
            },
        ],
    )


def test_endorsement_session(make_privmsg, make_incoming_privmsg, unauthorised_context, tested_vibecheck) -> None:
    ctx = AuthContext('person-uuid', ['group'])

    msg = Message(str(Code.RPL_NAMREPLY.value), params=['bot_nick', '@', '#channel', 'nick1 nick2'])
    tested_vibecheck.receive_message_in(msg)

    msg = Message(str(Code.RPL_ENDOFNAMES.value), params=['bot_nick', '#channel'])
    tested_vibecheck.receive_message_in(msg)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('NAMES #channel')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person :Skybird, this is Dropkick with a red dash alpha message in two parts. Break. Break. Stand by to copy the list of people who are currently in the channel:')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person :' + colored('nick2', Color.RED) + ' (?), ' + colored('nick1', Color.RED) + ' (?)')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person :If you would like to endorse any of them then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'. If you want to see the full report use the \'.vibecheck\' command.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_incoming_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick2', Color.RED) + ' (?), ' + colored('nick1', Color.RED) + ' (?)')
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :If you would like to endorse anyone then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_incoming_privmsg('.endorse nick1', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :You endorsed nick1!'),
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_incoming_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick1', Color.GREEN) + ' (^), ' + colored('nick2', Color.RED) + ' (?)')
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :If you would like to endorse anyone then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_incoming_privmsg('.endorse nick2', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :You endorsed nick2!'),
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_incoming_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick2', Color.GREEN) + ' (^), ' + colored('nick1', Color.GREEN) + ' (^)')
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :If you would like to endorse anyone then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_incoming_privmsg('.unendorse nick2', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :You unendorsed nick2!'),
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_incoming_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick1', Color.GREEN) + ' (^), ' + colored('nick2', Color.RED) + ' (?)'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :If you would like to endorse anyone then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'.')
            },
        ],
    )


def test_healthcheck(make_privmsg, make_incoming_privmsg, unauthorised_context, tested_vibecheck) -> None:
    tested_vibecheck.module.config['module_config']['botnet']['auth']['people'] = [
        {
            'uuid': 'person1-uuid',
            'groups': ['group'],
            'contact': ['person1'],
        },
        {
            'uuid': 'person2-uuid',
            'groups': ['group'],
            'contact': ['person2'],
        },
        {
            'uuid': 'person3-uuid',
            'groups': ['group'],
            'contact': ['person3'],
        },
    ]

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('NAMES #channel')
            },
        ],
    )

    msg = Message(str(Code.RPL_NAMREPLY.value), params=['bot_nick', '@', '#channel', 'nick1 nick2'])
    tested_vibecheck.receive_message_in(msg)

    msg = Message(str(Code.RPL_ENDOFNAMES.value), params=['bot_nick', '#channel'])
    tested_vibecheck.receive_message_in(msg)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('NAMES #channel')
            },
            {
                'msg': Message.new_from_string(
                    'PRIVMSG person1 :Skybird, this is Dropkick with a red dash alpha message in two parts. Break. Break. Stand by to copy the list of people who are currently in the channel:')
            },
            {
                'msg': Message.new_from_string(
                    'PRIVMSG person1 :' + colored('nick2', Color.RED) + ' (?), ' + colored('nick1',
                                                                                           Color.RED) + ' (?)'),
            },
            {
                'msg': Message.new_from_string(
                    'PRIVMSG person1 :If you would like to endorse any of them then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'. If you want to see the full report use the \'.vibecheck\' command.')
            },
            {
                'msg': Message.new_from_string(
                    'PRIVMSG person2 :Skybird, this is Dropkick with a red dash alpha message in two parts. Break. Break. Stand by to copy the list of people who are currently in the channel:')
            },
            {
                'msg': Message.new_from_string(
                    'PRIVMSG person2 :' + colored('nick2', Color.RED) + ' (?), ' + colored('nick1',
                                                                                           Color.RED) + ' (?)'),
            },
            {
                'msg': Message.new_from_string(
                    'PRIVMSG person2 :If you would like to endorse any of them then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'. If you want to see the full report use the \'.vibecheck\' command.')
            },
            {
                'msg': Message.new_from_string(
                    'PRIVMSG person3 :Skybird, this is Dropkick with a red dash alpha message in two parts. Break. Break. Stand by to copy the list of people who are currently in the channel:')
            },
            {
                'msg': Message.new_from_string(
                    'PRIVMSG person3 :' + colored('nick2', Color.RED) + ' (?), ' + colored('nick1',
                                                                                           Color.RED) + ' (?)'),
            },
            {
                'msg': Message.new_from_string(
                    'PRIVMSG person3 :If you would like to endorse any of them then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'. If you want to see the full report use the \'.vibecheck\' command.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()

    ctx = AuthContext('person1-uuid', ['group'])
    msg = make_incoming_privmsg('.vibecheck', target='bot_nick', nick="person1nick")
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG person1nick :Everyone currently in the channel: ' + colored('nick2', Color.RED) + ' (?), ' + colored('nick1', Color.RED) + ' (?)')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person1nick :If you would like to endorse anyone then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'.')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person1nick :Transparency: authorised group consists of person1-uuid, person2-uuid, person3-uuid; median last age of interaction with this module is '+ colored('never (!)', Color.RED) + ', max last age of interaction with this module is ' + colored('never (!)', Color.RED) + '.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()

    ctx = AuthContext('person2-uuid', ['group'])
    msg = make_incoming_privmsg('.vibecheck', target='bot_nick', nick="person2nick")
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG person2nick :Everyone currently in the channel: ' + colored('nick2', Color.RED) + ' (?), ' + colored('nick1', Color.RED) + ' (?)')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person2nick :If you would like to endorse anyone then you can privately use the \'.endorse NICK\' command in this buffer. Please note that this isn\'t a big decision as you can easily reverse it with \'.unendorse NICK\'.')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person2nick :Transparency: authorised group consists of person1-uuid, person2-uuid, person3-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('never (!)', Color.RED) + '.')
            },
        ],
    )


@pytest.fixture()
def tested_vibecheck(module_harness_factory, tmp_file):
    class TestVibecheck(Vibecheck):
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
                    'vibecheck': {
                        'data': tmp_file,
                        'channel': '#channel',
                        'authorised_group': 'group',
                    }
                },
            },
        }
    )

    return module_harness_factory.make(TestVibecheck, config)
