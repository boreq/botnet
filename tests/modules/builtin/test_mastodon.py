import pytest

from botnet.config import Config
from botnet.message import IncomingPrivateMessage
from botnet.message import Message
from botnet.modules import AuthContext
from botnet.modules.builtin.mastodon import Mastodon
from botnet.modules.builtin.mastodon import MastodonAPI
from botnet.modules.builtin.mastodon import Toot

from ...conftest import MakePrivmsgFixture
from ...conftest import ModuleHarness
from ...conftest import ModuleHarnessFactory


class FakeMastodonAPI(MastodonAPI):
    def __init__(self) -> None:
        self.toots: dict[str, Toot] = {}

    def toot(self, text: str) -> Toot:
        return self.toots[text]


class MastodonForTest(Mastodon):
    mock_api = FakeMastodonAPI()

    def _create_api(self, instance: str, access_token: str) -> MastodonAPI:
        return self.mock_api


def test_help(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_mastodon: ModuleHarness[MastodonForTest]) -> None:
    msg = IncomingPrivateMessage.new_from_message(make_privmsg('.help', target='#channel'))
    assert tested_mastodon.module.get_all_commands(msg, unauthorised_context) == {'help', 'toot'}


def test_toot(make_privmsg: MakePrivmsgFixture, unauthorised_context: AuthContext, tested_mastodon: ModuleHarness[MastodonForTest]) -> None:
    api = tested_mastodon.module.mock_api
    api.toots['hello world'] = Toot(url='https://example.com/@user/1')

    msg = make_privmsg('.toot hello world', nick='author', target='#channel')
    tested_mastodon.receive_message_in(msg)

    tested_mastodon.expect_message_out_signals([
        {
            'msg': Message.new_from_string('PRIVMSG #channel :https://example.com/@user/1')
        }
    ])


@pytest.fixture()
def tested_mastodon(module_harness_factory: ModuleHarnessFactory) -> ModuleHarness[MastodonForTest]:
    config = Config(
        {
            'module_config': {
                'botnet': {
                    'mastodon': {
                        'tooting': [
                            {
                                'command': 'toot',
                                'channels': ['#channel'],
                                'instance': 'https://example.com',
                                'access_token': 'token',
                            }
                        ]
                    }
                }
            }
        }
    )

    return module_harness_factory.make(MastodonForTest, config)
