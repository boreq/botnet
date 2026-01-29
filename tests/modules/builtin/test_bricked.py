import pytest

from botnet.config import Config
from botnet.message import Channel
from botnet.message import IncomingPrivateMessage
from botnet.message import Message
from botnet.message import Nick
from botnet.message import Target
from botnet.message import Text
from botnet.modules import AuthContext
from botnet.modules.builtin.bricked import Bricked
from botnet.modules.builtin.bricked import Status

from ...conftest import MakePrivmsgFixture
from ...conftest import ModuleHarness
from ...conftest import ModuleHarnessFactory


class FakeBrickedAPI:
    def get_status(self, id: str) -> Status:
        return Status(status=0.42)


def test_help(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_bricked: ModuleHarness[Bricked]) -> None:
    msg = IncomingPrivateMessage(sender=Nick('someone'), target=Target(Channel('#channel')), text=Text('some message'))
    assert tested_bricked.module.get_all_commands(msg, unauthorised_context) == {'help', 'issomeoneonone'}


def test_issomeoneonone(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_bricked: ModuleHarness[Bricked]) -> None:
    msg = make_privmsg('.issomeoneonone', target='#channel')
    tested_bricked.receive_message_in(msg)

    tested_bricked.expect_message_out_signals([
        {
            'msg': Message.new_from_string('PRIVMSG #channel :42%')
        },
    ])


@pytest.fixture()
def tested_bricked(module_harness_factory: ModuleHarnessFactory) -> ModuleHarness[Bricked]:
    class TestedBricked(Bricked):
        mock_api = FakeBrickedAPI()

        def _create_api(self, instance: str) -> FakeBrickedAPI:
            return self.mock_api

    config = Config(
        {
            'module_config': {
                'botnet': {
                    'bricked': {
                        'statuses': [
                            {
                                'commands': ['issomeoneonone'],
                                'channels': ['#channel'],
                                'instance': 'https://example.com',
                                'id': 'person_id',
                            }
                        ]
                    }
                }
            }
        }
    )

    return module_harness_factory.make(TestedBricked, config)
