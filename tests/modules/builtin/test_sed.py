from dataclasses import dataclass

import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.modules import AuthContext
from botnet.modules.builtin.sed import ParsedSedCommand
from botnet.modules.builtin.sed import Sed
from botnet.modules.builtin.sed import parse_message

from ...conftest import MakePrivmsgFixture
from ...conftest import ModuleHarness
from ...conftest import ModuleHarnessFactory


def test_parse_message() -> None:
    @dataclass
    class TestCase:
        input: str
        expected: ParsedSedCommand | None

    test_cases = [
        TestCase(
            input='s/a/b',
            expected=ParsedSedCommand(nick=None, a='a', b='b', flags=[]),
        ),
        TestCase(
            input='nick:s/a/b',
            expected=ParsedSedCommand(nick='nick', a='a', b='b', flags=[]),
        ),
        TestCase(
            input='nick: s/a/b',
            expected=ParsedSedCommand(nick='nick', a='a', b='b', flags=[]),
        ),
        TestCase(
            input='nick: s/lorem ipsum/something else',
            expected=ParsedSedCommand(nick='nick', a='lorem ipsum', b='something else', flags=[]),
        ),
        TestCase(
            input='s/a/b/',
            expected=ParsedSedCommand(nick=None, a='a', b='b', flags=[]),
        ),
        TestCase(
            input='nick:s/a/b/',
            expected=ParsedSedCommand(nick='nick', a='a', b='b', flags=[]),
        ),
        TestCase(
            input='nick: s/a/b/',
            expected=ParsedSedCommand(nick='nick', a='a', b='b', flags=[]),
        ),
        TestCase(
            input='nick: s/lorem ipsum/something else/',
            expected=ParsedSedCommand(nick='nick', a='lorem ipsum', b='something else', flags=[]),
        ),
        TestCase(
            input='s/a/b/gi',
            expected=ParsedSedCommand(nick=None, a='a', b='b', flags=['g', 'i']),
        ),
        TestCase(
            input='nick:s/a/b/gi',
            expected=ParsedSedCommand(nick='nick', a='a', b='b', flags=['g', 'i']),
        ),
        TestCase(
            input='nick: s/a/b/gi',
            expected=ParsedSedCommand(nick='nick', a='a', b='b', flags=['g', 'i']),
        ),
        TestCase(
            input='nick: s/lorem ipsum/something else/gi',
            expected=ParsedSedCommand(nick='nick', a='lorem ipsum', b='something else', flags=['g', 'i']),
        ),
    ]

    for test_case in test_cases:
        result = parse_message(test_case.input)
        assert result == test_case.expected


def test_parse_message_invalid() -> None:
    assert parse_message('lorem ipsum') is None


def test_replace_single(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_sed: ModuleHarness[Sed]) -> None:
    msg = make_privmsg('lorem ipsum lorem', nick='nick', target='#channel')
    tested_sed.receive_message_in(msg)

    msg = make_privmsg('nick: s/lorem/test', nick='someone', target='#channel')
    tested_sed.receive_message_in(msg)

    tested_sed.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :someone thinks nick meant to say: test ipsum lorem')
            }
        ]
    )


def test_replace_multiple(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_sed: ModuleHarness[Sed]) -> None:
    msg = make_privmsg('lorem ipsum one', nick='nick', target='#channel')
    tested_sed.receive_message_in(msg)

    msg = make_privmsg('lorem ipsum two', nick='nick', target='#channel')
    tested_sed.receive_message_in(msg)

    msg = make_privmsg('nick: s/lorem/test', nick='someone', target='#channel')
    tested_sed.receive_message_in(msg)

    tested_sed.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :someone thinks nick meant to say: test ipsum two')
            }
        ]
    )


def test_replace_global(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_sed: ModuleHarness[Sed]) -> None:
    msg = make_privmsg('lorem ipsum lorem', nick='nick', target='#channel')
    tested_sed.receive_message_in(msg)

    msg = make_privmsg('nick: s/lorem/test/g', nick='someone', target='#channel')
    tested_sed.receive_message_in(msg)

    tested_sed.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :someone thinks nick meant to say: test ipsum test')
            }
        ]
    )


def test_same_channel(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_sed: ModuleHarness[Sed]) -> None:
    msg = make_privmsg('Hellp!', nick='author', target='#channel')
    tested_sed.receive_message_in(msg)

    msg = make_privmsg('s/Hellp!/Hello!', nick='author', target='#channel')
    tested_sed.receive_message_in(msg)

    tested_sed.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :author meant to say: Hello!')
            }
        ]
    )


@pytest.fixture()
def tested_sed(module_harness_factory: ModuleHarnessFactory, tmp_file: str) -> ModuleHarness[Sed]:
    with open(tmp_file, 'w', encoding='utf-8') as f:
        f.write('{"messages": {}}')

    config = {
        'module_config': {
            'botnet': {
                'sed': {
                    'message_data': tmp_file,
                }
            }
        }
    }

    return module_harness_factory.make(Sed, Config(config))
