import threading
import requests
from ...message import IncomingPrivateMessage
from .. import BaseResponder, command, parse_command, Args
from ..base import AuthContext
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Metar:
    text: str


class VatsimAPI(Protocol):
    def get_metar(self, icao: str) -> Metar:
        ...


class RestVatsimAPI:
    def __init__(self, api_url_template: str) -> None:
        self._api_url_template = api_url_template

    def get_metar(self, icao: str) -> Metar:
        url = self._api_url_template % icao
        r = requests.get(url)
        r.raise_for_status()
        return Metar(text=r.text)


@dataclass()
class VatsimConfig:
    metar_api_url: str | None

    def __post_init__(self):
        if self.metar_api_url is not None and self.metar_api_url == '':
            raise ValueError('metar_api_url cannot be an empty string')


class Vatsim(BaseResponder[VatsimConfig]):
    """Various VATSIM related features.

    Example module config:

        "botnet": {
            "vatsim": {
                "metar_api_url": "https://metar.vatsim.net/metar.php?id=%s",
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'vatsim'
    config_class = VatsimConfig

    default_metar_api_url = 'https://metar.vatsim.net/metar.php?id=%s'

    @command('metar')
    @parse_command([('icao', 1)])
    def command_metar(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Returns a METAR for the given airport.

        Syntax: metar ICAO
        """
        icao = args['icao'][0]

        def f() -> None:
            api = self._create_api()
            metar = api.get_metar(icao)
            if not metar.text:
                self.respond(msg, 'Server didn\'t return an error but the response is empty.')
            else:
                self.respond(msg, metar.text)

        t = threading.Thread(target=f)
        t.start()

    def _create_api(self) -> VatsimAPI:
        config = self.get_config()
        return RestVatsimAPI(config.metar_api_url if config.metar_api_url is not None else self.default_metar_api_url)


mod = Vatsim
