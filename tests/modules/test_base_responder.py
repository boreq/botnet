from dataclasses import dataclass
from typing import Callable

import pytest

from botnet.config import Config
from botnet.message import Channel
from botnet.message import IncomingPrivateMessage
from botnet.message import Message
from botnet.message import Nick
from botnet.message import Target
from botnet.message import Text
from botnet.modules import BaseResponder

from ..conftest import ModuleHarness
from ..conftest import ModuleHarnessFactory


@dataclass()
class BaseResponderConfigForTest:
    pass


class BaseResponderForTest(BaseResponder[BaseResponderConfigForTest]):
    pass


def test_respond(subtests: pytest.Subtests, tested_base_responder: Callable[[], ModuleHarness[BaseResponderForTest]]) -> None:
    @dataclass
    class TestCase:
        message_target: str
        pm: bool
        expected: str

    test_cases = [
        TestCase(
            message_target='#channel',
            pm=False,
            expected='PRIVMSG #channel :some response',
        ),
        TestCase(
            message_target='bot_nick',
            pm=False,
            expected='PRIVMSG nick :some response',
        ),
        TestCase(
            message_target='#channel',
            pm=True,
            expected='PRIVMSG nick :some response',
        ),
        TestCase(
            message_target='bot_nick',
            pm=True,
            expected='PRIVMSG nick :some response',
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            msg = IncomingPrivateMessage(
                sender=Nick('nick'),
                target=Target.new_from_string(test_case.message_target),
                text=Text('some text'),
            )

            m = tested_base_responder()
            m.module.respond(msg, 'some response', pm=test_case.pm)

            m.expect_message_out_signals(
                [
                    {
                        'msg': Message.new_from_string(test_case.expected)
                    }
                ]
            )
            m.stop()


def test_get_command_name(subtests: pytest.Subtests, tested_base_responder: Callable[[], ModuleHarness[BaseResponderForTest]]) -> None:
    @dataclass
    class TestCase:
        text: str
        expected: str | None

    test_cases = [
        TestCase(
            text='.test',
            expected='test',
        ),
        TestCase(
            text='.test arg',
            expected='test',
        ),
        TestCase(
            text=':test',
            expected=None,
        ),
        TestCase(
            text=':test arg',
            expected=None,
        ),
        TestCase(
            text='test',
            expected=None,
        ),
        TestCase(
            text='test arg',
            expected=None,
        ),
        TestCase(
            text=':',
            expected=None,
        ),
        TestCase(
            text='.',
            expected=None,
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            msg = IncomingPrivateMessage(
                sender=Nick('nick'),
                target=Target(Channel('#channel')),
                text=Text(test_case.text),
            )

            m = tested_base_responder()
            assert m.module.get_command_name(msg) == test_case.expected
            m.stop()


@pytest.fixture()
def tested_base_responder(module_harness_factory: ModuleHarnessFactory) -> Callable[[], ModuleHarness[BaseResponderForTest]]:
    def make() -> ModuleHarness[BaseResponderForTest]:
        config = Config({})
        return module_harness_factory.make(BaseResponderForTest, config)
    return make
