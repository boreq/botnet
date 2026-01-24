from botnet.modules.builtin.vatsim import Vatsim, VatsimAPI, Metar
from botnet.message import Message
from botnet.config import Config
import pytest


class FakeVatsimAPI(VatsimAPI):
    def __init__(self):
        self.mock_metars = {}

    def get_metar(self, icao: str) -> Metar:
        return self.mock_metars.get(icao, Metar(text=''))


def test_help(make_privmsg, make_incoming_privmsg, unauthorised_context, test_vatsim):
    msg = make_incoming_privmsg('.help', target='#channel')
    assert test_vatsim.module.get_all_commands(msg, unauthorised_context) == {'help', 'metar'}


def test_metar(make_privmsg, make_incoming_privmsg, unauthorised_context, test_vatsim) -> None:
    api: FakeVatsimAPI = test_vatsim.module.mock_api
    api.mock_metars['EGLL'] = Metar(text='EGLL 241350Z 02010KT 9999 NCD 08/04 Q1013')

    msg = make_incoming_privmsg('.metar EGLL', nick='author', target='#channel')
    test_vatsim.receive_auth_message_in(msg, unauthorised_context)

    test_vatsim.expect_message_out_signals([
        {
            'msg': Message.new_from_string('PRIVMSG #channel :EGLL 241350Z 02010KT 9999 NCD 08/04 Q1013')
        }
    ])


def test_metar_empty(make_privmsg, make_incoming_privmsg, unauthorised_context, test_vatsim) -> None:
    api: FakeVatsimAPI = test_vatsim.module.mock_api
    api.mock_metars['EGLL'] = Metar(text='')

    msg = make_incoming_privmsg('.metar EGLL', nick='author', target='#channel')
    test_vatsim.receive_auth_message_in(msg, unauthorised_context)

    test_vatsim.expect_message_out_signals([
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Server didn't return an error but the response is empty.")
        }
    ])


@pytest.fixture()
def test_vatsim(module_harness_factory):
    class TestVatsim(Vatsim):
        mock_api = FakeVatsimAPI()

        def _create_api(self, api_url_template: str) -> VatsimAPI:
            return self.mock_api

    config = Config(
        {
            'module_config': {
                'botnet': {
                    'vatsim': {
                        'metar_api_url': 'https://example.com/metar?id=%s'
                    }
                }
            }
        }
    )

    return module_harness_factory.make(TestVatsim, config)
