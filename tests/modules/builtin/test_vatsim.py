import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.modules.builtin.vatsim import Metar
from botnet.modules.builtin.vatsim import Vatsim
from botnet.modules.builtin.vatsim import VatsimAPI

from ...conftest import MakePrivmsgFixture


class FakeVatsimAPI(VatsimAPI):
    def __init__(self):
        self.mock_metars = {}

    def get_metar(self, icao: str) -> Metar:
        return self.mock_metars.get(icao, Metar(text=''))


def test_help(make_privmsg: MakePrivmsgFixture, unauthorised_context, tested_vatsim):
    msg = make_privmsg('.help', target='#channel')
    assert tested_vatsim.module.get_all_commands(msg, unauthorised_context) == {'help', 'metar'}


def test_metar(make_privmsg: MakePrivmsgFixture, unauthorised_context, tested_vatsim) -> None:
    api: FakeVatsimAPI = tested_vatsim.module.mock_api
    api.mock_metars['EGLL'] = Metar(text='EGLL 241350Z 02010KT 9999 NCD 08/04 Q1013')

    msg = make_privmsg('.metar EGLL', nick='author', target='#channel')
    tested_vatsim.receive_auth_message_in(msg, unauthorised_context)

    tested_vatsim.expect_message_out_signals([
        {
            'msg': Message.new_from_string('PRIVMSG #channel :EGLL 241350Z 02010KT 9999 NCD 08/04 Q1013')
        }
    ])


def test_metar_empty(make_privmsg: MakePrivmsgFixture, unauthorised_context, tested_vatsim) -> None:
    api: FakeVatsimAPI = tested_vatsim.module.mock_api
    api.mock_metars['EGLL'] = Metar(text='')

    msg = make_privmsg('.metar EGLL', nick='author', target='#channel')
    tested_vatsim.receive_auth_message_in(msg, unauthorised_context)

    tested_vatsim.expect_message_out_signals([
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Server didn't return an error but the response is empty.")
        }
    ])


@pytest.fixture()
def tested_vatsim(module_harness_factory):
    class TestedVatsim(Vatsim):
        mock_api = FakeVatsimAPI()

        def _create_api(self) -> VatsimAPI:
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

    return module_harness_factory.make(TestedVatsim, config)
