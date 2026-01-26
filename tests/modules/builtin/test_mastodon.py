import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.modules.builtin.mastodon import Mastodon
from botnet.modules.builtin.mastodon import MastodonAPI
from botnet.modules.builtin.mastodon import Toot


class FakeMastodonAPI(MastodonAPI):
    def __init__(self):
        self.toots = {}

    def toot(self, text: str) -> Toot:
        return self.toots.get(text, Toot(url=''))


def test_help(make_privmsg, make_incoming_privmsg, unauthorised_context, test_mastodon) -> None:
    msg = make_incoming_privmsg('.help', target='#channel')
    assert test_mastodon.module.get_all_commands(msg, unauthorised_context) == {'help', 'toot'}


def test_toot(make_privmsg, make_incoming_privmsg, unauthorised_context, test_mastodon) -> None:
    api: FakeMastodonAPI = test_mastodon.module.mock_api
    api.toots['hello world'] = Toot(url='https://example.com/@user/1')

    msg = make_privmsg('.toot hello world', nick='author', target='#channel')
    test_mastodon.receive_message_in(msg)

    test_mastodon.expect_message_out_signals([
        {
            'msg': Message.new_from_string('PRIVMSG #channel :https://example.com/@user/1')
        }
    ])


@pytest.fixture()
def test_mastodon(module_harness_factory):
    class TestMastodon(Mastodon):
        mock_api = FakeMastodonAPI()

        def _create_api(self, instance: str, access_token: str) -> MastodonAPI:
            return self.mock_api

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

    return module_harness_factory.make(TestMastodon, config)
