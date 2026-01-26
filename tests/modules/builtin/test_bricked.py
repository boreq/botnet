import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.modules.builtin.bricked import Bricked
from botnet.modules.builtin.bricked import Status


class FakeBrickedAPI:
    def get_status(self, id: str):
        return Status(status=0.42)


def test_help(make_privmsg, make_incoming_privmsg, unauthorised_context, test_bricked):
    msg = make_incoming_privmsg('.help', target='#channel')
    assert test_bricked.module.get_all_commands(msg, unauthorised_context) == {'help', 'issomeoneonone'}


def test_issomeoneonone(make_privmsg, make_incoming_privmsg, unauthorised_context, test_bricked):
    msg = make_privmsg('.issomeoneonone', target='#channel')
    test_bricked.receive_message_in(msg)

    test_bricked.expect_message_out_signals([
        {
            'msg': Message.new_from_string('PRIVMSG #channel :42%')
        },
    ])


@pytest.fixture()
def test_bricked(module_harness_factory):
    class TestBricked(Bricked):
        mock_api = FakeBrickedAPI()

        def _create_api(self, instance: str):
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

    return module_harness_factory.make(TestBricked, config)
