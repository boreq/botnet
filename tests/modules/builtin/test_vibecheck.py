from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Optional

import pytest

from botnet.codes import Code
from botnet.config import Config
from botnet.message import Message
from botnet.message import Nick
from botnet.modules import AuthContext
from botnet.modules.builtin.vibecheck import EnforcementAction
from botnet.modules.builtin.vibecheck import PersonaReport
from botnet.modules.builtin.vibecheck import Vibecheck
from botnet.modules.lib import Color
from botnet.modules.lib import colored

from ...conftest import MakePrivmsgFixture
from ...conftest import ModuleHarness
from ...conftest import ModuleHarnessFactory


class VibecheckForTest(Vibecheck):

    def _now(self) -> datetime:
        return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_pester(tested_vibecheck: ModuleHarness[Vibecheck]) -> None:
    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('NAMES #channel')
            },
        ],
    )

    for nick in ['nick1', 'nick2']:
        msg = Message(
            prefix='%s!~user@1-2-3-4.example.com' % nick,
            command='JOIN',
            params=['#channel']
        )
        tested_vibecheck.receive_message_in(msg)

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
                'msg': Message.new_from_string('PRIVMSG person :' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + '), ' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')'),
            },
            {
                'msg': Message.new_from_string("PRIVMSG person :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
        ],
    )


def test_endorsement_session(make_privmsg: MakePrivmsgFixture, tested_vibecheck: ModuleHarness[Vibecheck]) -> None:
    ctx = AuthContext('person-uuid', ['group'])

    for nick in ['nick1', 'nick2']:
        msg = Message(
            prefix='%s!~user@1-2-3-4.example.com' % nick,
            command='JOIN',
            params=['#channel']
        )
        tested_vibecheck.receive_message_in(msg)

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
                'msg': Message.new_from_string('PRIVMSG person :' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + '), ' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG person :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + '), ' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :Transparency: authorised group consists of person-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + '.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_privmsg('.endorse nick1', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :You endorsed nick1!'),
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick1', Color.GREEN) + ' (^), ' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :Transparency: authorised group consists of person-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + '.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_privmsg('.endorse nick2', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :You endorsed nick2!'),
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick2', Color.GREEN) + ' (^), ' + colored('nick1', Color.GREEN) + ' (^)')
            },
            {
                'msg': Message.new_from_string("PRIVMSG nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :Transparency: authorised group consists of person-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + '.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_privmsg('.unendorse nick2', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :You unendorsed nick2!'),
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()
    msg = make_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick1', Color.GREEN) + ' (^), ' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :Transparency: authorised group consists of person-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + '.')
            },
        ],
    )


def test_healthcheck(make_privmsg: MakePrivmsgFixture, tested_vibecheck: ModuleHarness[Vibecheck]) -> None:
    some_authorisations = [
        {
            'logged_in_as': {
                'nick': 'ircnick',
            },
        },
    ]

    tested_vibecheck.module._config['module_config']['botnet']['auth']['people'] = [
        {
            'uuid': 'person1-uuid',
            'authorisations': some_authorisations,
            'groups': ['group'],
            'contact': ['person1'],
        },
        {
            'uuid': 'person2-uuid',
            'authorisations': some_authorisations,
            'groups': ['group'],
            'contact': ['person2'],
        },
        {
            'uuid': 'person3-uuid',
            'authorisations': some_authorisations,
            'groups': ['group'],
            'contact': ['person3'],
        },
    ]

    for nick in ['nick1', 'nick2']:
        msg = Message(
            prefix='%s!~user@1-2-3-4.example.com' % nick,
            command='JOIN',
            params=['#channel']
        )
        tested_vibecheck.receive_message_in(msg)

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
                'msg': Message.new_from_string('PRIVMSG person1 :' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + '), ' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')'),
            },
            {
                'msg': Message.new_from_string("PRIVMSG person1 :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG person2 :Skybird, this is Dropkick with a red dash alpha message in two parts. Break. Break. Stand by to copy the list of people who are currently in the channel:')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person2 :' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + '), ' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')'),
            },
            {
                'msg': Message.new_from_string("PRIVMSG person2 :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG person3 :Skybird, this is Dropkick with a red dash alpha message in two parts. Break. Break. Stand by to copy the list of people who are currently in the channel:')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person3 :' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + '), ' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')'),
            },
            {
                'msg': Message.new_from_string("PRIVMSG person3 :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()

    ctx = AuthContext('person1-uuid', ['group'])
    msg = make_privmsg('.vibecheck', target='bot_nick', nick="person1nick")
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG person1nick :Everyone currently in the channel: ' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + '), ' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG person1nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG person1nick :Transparency: authorised group consists of person1-uuid, person2-uuid, person3-uuid; median last age of interaction with this module is ' + colored('never (!)', Color.RED) + ', max last age of interaction with this module is ' + colored('never (!)', Color.RED) + '.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()

    ctx = AuthContext('person2-uuid', ['group'])
    msg = make_privmsg('.vibecheck', target='bot_nick', nick="person2nick")
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG person2nick :Everyone currently in the channel: ' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + '), ' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG person2nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG person2nick :Transparency: authorised group consists of person1-uuid, person2-uuid, person3-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('never (!)', Color.RED) + '.')
            },
        ],
    )


def test_part_updates_names_cache(make_privmsg: MakePrivmsgFixture, tested_vibecheck: ModuleHarness[Vibecheck]) -> None:
    ctx = AuthContext('person-uuid', ['group'])

    msg = Message(str(Code.RPL_NAMREPLY.value), params=['bot_nick', '@', '#channel', 'nick1 nick2'])
    tested_vibecheck.receive_message_in(msg)

    msg = Message(str(Code.RPL_ENDOFNAMES.value), params=['bot_nick', '#channel'])
    tested_vibecheck.receive_message_in(msg)

    tested_vibecheck.reset_message_out_signals()

    msg = make_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + '), ' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :Transparency: authorised group consists of person-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + '.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()

    msg = Message.new_from_string(':nick1!user@host PART #channel')
    tested_vibecheck.receive_message_in(msg)

    msg = make_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :Transparency: authorised group consists of person-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + '.')
            },
        ],
    )


def test_join_updates_names_cache(make_privmsg: MakePrivmsgFixture, tested_vibecheck: ModuleHarness[Vibecheck]) -> None:
    ctx = AuthContext('person-uuid', ['group'])

    msg = Message(str(Code.RPL_NAMREPLY.value), params=['bot_nick', '@', '#channel', 'nick1'])
    tested_vibecheck.receive_message_in(msg)

    msg = Message(str(Code.RPL_ENDOFNAMES.value), params=['bot_nick', '#channel'])
    tested_vibecheck.receive_message_in(msg)

    tested_vibecheck.reset_message_out_signals()

    msg = make_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :Transparency: authorised group consists of person-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + '.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()

    msg = Message.new_from_string(':nick2!user@host JOIN #channel')
    tested_vibecheck.receive_message_in(msg)

    msg = make_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + '), ' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :Transparency: authorised group consists of person-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + '.')
            },
        ],
    )


def test_quit_updates_names_cache(make_privmsg: MakePrivmsgFixture, tested_vibecheck: ModuleHarness[Vibecheck]) -> None:
    ctx = AuthContext('person-uuid', ['group'])

    msg = Message(str(Code.RPL_NAMREPLY.value), params=['bot_nick', '@', '#channel', 'nick1 nick2'])
    tested_vibecheck.receive_message_in(msg)

    msg = Message(str(Code.RPL_ENDOFNAMES.value), params=['bot_nick', '#channel'])
    tested_vibecheck.receive_message_in(msg)

    tested_vibecheck.reset_message_out_signals()

    msg = make_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + '), ' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :Transparency: authorised group consists of person-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + '.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()

    msg = Message.new_from_string(':nick1!user@host QUIT :Quit message')
    tested_vibecheck.receive_message_in(msg)

    msg = make_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :Transparency: authorised group consists of person-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + '.')
            },
        ],
    )


def test_kick_updates_names_cache(make_privmsg: MakePrivmsgFixture, tested_vibecheck: ModuleHarness[Vibecheck]) -> None:
    ctx = AuthContext('person-uuid', ['group'])

    msg = Message(str(Code.RPL_NAMREPLY.value), params=['bot_nick', '@', '#channel', 'nick1 nick2'])
    tested_vibecheck.receive_message_in(msg)

    msg = Message(str(Code.RPL_ENDOFNAMES.value), params=['bot_nick', '#channel'])
    tested_vibecheck.receive_message_in(msg)

    tested_vibecheck.reset_message_out_signals()

    msg = make_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + '), ' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :Transparency: authorised group consists of person-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + '.')
            },
        ],
    )

    tested_vibecheck.reset_message_out_signals()

    msg = Message.new_from_string(':kicker!user@host KICK #channel nick1')
    tested_vibecheck.receive_message_in(msg)

    msg = make_privmsg('.vibecheck', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)

    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :Everyone currently in the channel: ' + colored('nick2', Color.RED) + ' (?' + colored('0', Color.RED) + ')')
            },
            {
                'msg': Message.new_from_string("PRIVMSG nick :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :Transparency: authorised group consists of person-uuid; median last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + ', max last age of interaction with this module is ' + colored('in the last 0 days', Color.GREEN) + '.')
            },
        ],
    )


def test_vibecheck_nick(make_privmsg: MakePrivmsgFixture, tested_vibecheck: ModuleHarness[Vibecheck]) -> None:
    ctx = AuthContext('person-uuid', ['group'])

    msg = Message(str(Code.RPL_NAMREPLY.value), params=['bot_nick', '@', '#channel', 'nick'])
    tested_vibecheck.receive_message_in(msg)

    msg = Message(str(Code.RPL_ENDOFNAMES.value), params=['bot_nick', '#channel'])
    tested_vibecheck.receive_message_in(msg)

    tested_vibecheck.reset_message_out_signals()

    msg = make_privmsg('.vibecheck testnick', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)
    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :' + colored('testnick', Color.RED) + ' (?' + colored('0', Color.RED) + ')'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  All nicks: testnick'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First message: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last message: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First join: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last join: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First kick: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last kick: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First seen in the channel: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last seen in the channel: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last automated ping: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :' + colored('  Was NOT endorsed by you.', Color.RED)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :' + colored('  Was NOT endorsed by anyone.', Color.RED)),
            },
        ],
    )
    tested_vibecheck.reset_message_out_signals()

    msg = Message.new_from_string(':testnick!user@host JOIN #channel')
    tested_vibecheck.receive_message_in(msg)

    msg = make_privmsg('.vibecheck testnick', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)
    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :' + colored('testnick', Color.RED) + ' (?' + colored('0', Color.RED) + ')'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  All nicks: testnick'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First message: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last message: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First join: ' + colored('2 years ago', Color.RED)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last join: 2 years ago'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First kick: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last kick: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First seen in the channel: ' + colored('2 years ago', Color.RED)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last seen in the channel: ' + colored('2 years ago', Color.GREEN)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last automated ping: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :' + colored('  Was NOT endorsed by you.', Color.RED)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :' + colored('  Was NOT endorsed by anyone.', Color.RED)),
            },
        ],
    )
    tested_vibecheck.reset_message_out_signals()

    msg = make_privmsg('hello world', target='#channel', nick='testnick')
    tested_vibecheck.receive_message_in(msg)

    msg = make_privmsg('.vibecheck testnick', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)
    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :' + colored('testnick', Color.RED) + ' (?' + colored('0', Color.RED) + ')'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  All nicks: testnick'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First message: ' + colored('2 years ago', Color.RED)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last message: ' + colored('2 years ago', Color.GREEN)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First join: ' + colored('2 years ago', Color.RED)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last join: 2 years ago'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First kick: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last kick: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First seen in the channel: ' + colored('2 years ago', Color.RED)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last seen in the channel: ' + colored('2 years ago', Color.GREEN)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last automated ping: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :' + colored('  Was NOT endorsed by you.', Color.RED)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :' + colored('  Was NOT endorsed by anyone.', Color.RED)),
            },
        ],
    )
    tested_vibecheck.reset_message_out_signals()

    msg = Message.new_from_string(':kicker!user@host KICK #channel testnick')
    tested_vibecheck.receive_message_in(msg)

    msg = make_privmsg('.vibecheck testnick', target='bot_nick')
    tested_vibecheck.receive_auth_message_in(msg, ctx)
    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG nick :' + colored('testnick', Color.RED) + ' (?' + colored('0', Color.RED) + ')'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  All nicks: testnick'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First message: ' + colored('2 years ago', Color.RED)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last message: ' + colored('2 years ago', Color.GREEN)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First join: ' + colored('2 years ago', Color.RED)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last join: 2 years ago'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First kick: 2 years ago'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last kick: 2 years ago'),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  First seen in the channel: ' + colored('2 years ago', Color.RED)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last seen in the channel: ' + colored('2 years ago', Color.GREEN)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :  Last automated ping: ' + colored('unknown', Color.YELLOW)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :' + colored('  Was NOT endorsed by you.', Color.RED)),
            },
            {
                'msg': Message.new_from_string('PRIVMSG nick :' + colored('  Was NOT endorsed by anyone.', Color.RED)),
            },
        ],
    )


def test_determine_enforcement_action() -> None:
    @dataclass
    class TestCase:
        description: str
        endorsements: set[str]
        last_join: Optional[datetime]
        last_message: Optional[datetime]
        last_automated_ping: Optional[datetime]
        now: datetime
        expected: EnforcementAction

    now = datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc)

    test_cases = [
        TestCase(
            description='endorsed persona is never actioned',
            endorsements={'some-uuid'},
            last_join=None,
            last_message=None,
            last_automated_ping=None,
            now=now,
            expected=EnforcementAction.NONE,
        ),
        TestCase(
            description='no data at all results in ping',
            endorsements=set(),
            last_join=None,
            last_message=None,
            last_automated_ping=None,
            now=now,
            expected=EnforcementAction.PING,
        ),
        TestCase(
            description='join within grace period results in none',
            endorsements=set(),
            last_join=now - timedelta(hours=0.5),
            last_message=None,
            last_automated_ping=None,
            now=now,
            expected=EnforcementAction.NONE,
        ),
        TestCase(
            description='message within grace period results in none',
            endorsements=set(),
            last_join=None,
            last_message=now - timedelta(hours=48),
            last_automated_ping=None,
            now=now,
            expected=EnforcementAction.NONE,
        ),
        TestCase(
            description='join grace expired, no ping yet results in ping',
            endorsements=set(),
            last_join=now - timedelta(hours=2),
            last_message=None,
            last_automated_ping=None,
            now=now,
            expected=EnforcementAction.PING,
        ),
        TestCase(
            description='join grace expired, pinged recently results in none',
            endorsements=set(),
            last_join=now - timedelta(hours=2),
            last_message=None,
            last_automated_ping=now - timedelta(hours=6),
            now=now,
            expected=EnforcementAction.NONE,
        ),
        TestCase(
            description='join grace expired, last ping too old results in ping again',
            endorsements=set(),
            last_join=now - timedelta(hours=2),
            last_message=None,
            last_automated_ping=now - timedelta(hours=73),
            now=now,
            expected=EnforcementAction.PING,
        ),
        TestCase(
            description='join grace expired by more than kicking threshold results in kick',
            endorsements=set(),
            last_join=now - timedelta(hours=2 + 24),
            last_message=None,
            last_automated_ping=None,
            now=now,
            expected=EnforcementAction.KICK,
        ),
        TestCase(
            description='message grace expired, no ping yet results in ping',
            endorsements=set(),
            last_join=None,
            last_message=now - timedelta(hours=73),
            last_automated_ping=None,
            now=now,
            expected=EnforcementAction.PING,
        ),
        TestCase(
            description='message grace expired by more than kicking threshold results in kick',
            endorsements=set(),
            last_join=None,
            last_message=now - timedelta(hours=72 + 24 + 1),
            last_automated_ping=None,
            now=now,
            expected=EnforcementAction.KICK,
        ),
        TestCase(
            description='join grace expired but message grace still active results in none',
            endorsements=set(),
            last_join=now - timedelta(hours=25),
            last_message=now - timedelta(hours=48),
            last_automated_ping=None,
            now=now,
            expected=EnforcementAction.NONE,
        ),
    ]

    for tc in test_cases:
        report = PersonaReport(
            nicks_now_in_the_channel=[Nick('testnick')],
            all_nicks=[Nick('testnick')],
            endorsements=tc.endorsements,
            first_message=None,
            last_message=tc.last_message,
            first_join=None,
            last_join=tc.last_join,
            first_kick=None,
            last_kick=None,
            first_seen_in_the_channel=None,
            last_seen_in_the_channel=None,
            last_automated_ping=tc.last_automated_ping,
        )
        result = report.determine_enforcement_action(tc.now)
        assert result == tc.expected, f'Failed: {tc.description!r}: expected {tc.expected}, got {result}'


def test_messages_only_once(tested_vibecheck: ModuleHarness[Vibecheck]) -> None:
    tested_vibecheck.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('NAMES #channel')
            },
        ],
    )

    msg = Message(str(Code.RPL_NAMREPLY.value), params=['bot_nick', '@', '#channel', 'nick1'])
    tested_vibecheck.receive_message_in(msg)

    msg = Message(str(Code.RPL_ENDOFNAMES.value), params=['bot_nick', '#channel'])
    tested_vibecheck.receive_message_in(msg)

    tested_vibecheck.module._update()
    tested_vibecheck.module._update()

    def wait_condition(trapped: list[dict[str, Any]]) -> None:
        first_four = [
            {
                'msg': Message.new_from_string('NAMES #channel')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person :Skybird, this is Dropkick with a red dash alpha message in two parts. Break. Break. Stand by to copy the list of people who are currently in the channel:')
            },
            {
                'msg': Message.new_from_string('PRIVMSG person :' + colored('nick1', Color.RED) + ' (?' + colored('0', Color.RED) + ')'),
            },
            {
                'msg': Message.new_from_string("PRIVMSG person :If you would like to endorse anyone then you can privately use '.endorse NICK' in this buffer. Please note that this isn't a big decision as you can easily reverse it with '.unendorse NICK'. The full report can always be recalled with '.vibecheck'. If you want to know more about a nick use '.vibecheck NICK'.")
            },
        ]
        assert len(trapped) == 5
        assert trapped[:4] == first_four
        assert 'nick1:' in trapped[4]['msg'].to_string()

    tested_vibecheck.message_out_trap.wait(wait_condition)


@pytest.fixture()
def tested_vibecheck(module_harness_factory: ModuleHarnessFactory, tmp_file: str) -> ModuleHarness[VibecheckForTest]:
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
                                'authorisations': [
                                    {
                                        'logged_in_as': {
                                            'nick': 'ircnick',
                                        },
                                    },
                                ],
                                'groups': ['group'],
                                'contact': ['person'],
                            }
                        ]
                    },
                    'vibecheck': {
                        'data': tmp_file,
                        'channel': '#channel',
                        'authorised_group': 'group',
                    },
                },
            },
        }
    )

    m = module_harness_factory.make(VibecheckForTest, config)
    m.module.start()
    return m
