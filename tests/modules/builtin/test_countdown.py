from datetime import date

import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.modules.builtin.countdown import Countdown

from ...conftest import MakePrivmsgFixture
from ...conftest import ModuleHarness
from ...conftest import ModuleHarnessFactory


def test_camp(make_privmsg: MakePrivmsgFixture, tested_countdown: ModuleHarness[Countdown]) -> None:
    tested_countdown.receive_message_in(make_privmsg('.camp'))
    tested_countdown.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :It already happened!')
            }
        ]
    )


def test_congress(make_privmsg: MakePrivmsgFixture, tested_countdown: ModuleHarness[Countdown]) -> None:
    tested_countdown.receive_message_in(make_privmsg('.congress'))
    tested_countdown.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :14 days left!')
            }
        ]
    )


def test_countdown_summary(make_privmsg: MakePrivmsgFixture, tested_countdown: ModuleHarness[Countdown]) -> None:
    tested_countdown.receive_message_in(make_privmsg('.summary'))
    tested_countdown.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :camp: It already happened, congress: 14 days left')
            }
        ]
    )


@pytest.fixture()
def tested_countdown(module_harness_factory: ModuleHarnessFactory) -> ModuleHarness[Countdown]:
    config = {
        'module_config': {
            'botnet': {
                'countdown': {
                    'summary_command': 'summary',
                    'commands': [
                        {
                            'names': ['camp'],
                            'year': 2023,
                            'month': 8,
                            'day': 15,
                        },
                        {
                            'names': ['congress'],
                            'year': 2025,
                            'month': 8,
                            'day': 15,
                        }
                    ]
                }
            }
        }
    }

    class TestedCountdown(Countdown):
        def _now(self) -> date:
            return date(2025, 8, 1)

    return module_harness_factory.make(TestedCountdown, Config(config))
