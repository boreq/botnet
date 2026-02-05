from dataclasses import dataclass
from typing import Protocol

import requests
from prometheus_client.parser import text_string_to_metric_families

from ...message import IncomingPrivateMessage
from .. import AuthContext
from .. import BaseResponder
from .. import command


@dataclass()
class Cows:
    happily_grazing: int
    ran_away: int
    have_not_checked_yet: int


class MoooodotfarmAPI(Protocol):

    def cows(self) -> Cows:
        ...


class MetricsMoodotfarmAPI(MoooodotfarmAPI):

    def __init__(self) -> None:
        self._url = 'https://moooo.farm/metrics'

    def cows(self) -> Cows:
        response = self._get()
        metrics = {}

        for family in text_string_to_metric_families(response.text):
            if family.name == 'moooodotfarm_herd_numbers':
                for sample in family.samples:
                    status = sample.labels.get('status')
                    if status:
                        metrics[status] = int(sample.value)

        return Cows(
            happily_grazing=metrics.get('happily_grazing', 0),
            ran_away=metrics.get('ran_away', 0),
            have_not_checked_yet=metrics.get('have_not_checked_yet', 0),
        )

    def _get(self) -> requests.Response:
        response = requests.get(self._url)
        response.raise_for_status()
        return response


@dataclass()
class MoooodotfarmConfig:
    pass


class Moooodotfarm(BaseResponder[MoooodotfarmConfig]):
    """Reports status of cows grazing at https://moooo.farm.

    Example module config:

        "botnet": {
            "moooodotfarm": {
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'moooodotfarm'
    config_class = MoooodotfarmConfig

    @command('cows')
    def cows(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
        api = self._get_api()
        cows = api.cows()

        responses = []

        if cows.happily_grazing:
            responses.append(f'There are {cows.happily_grazing} cows happily grazing!')

        if cows.ran_away:
            responses.append(f'There are {cows.ran_away} cows that have run away!')

        if cows.have_not_checked_yet:
            responses.append(f'There are {cows.have_not_checked_yet} cows that have not been checked yet!')

        if not responses:
            responses.append('There are no cows at the moment :(((((')

        for response in responses:
            self.respond(msg, response)

    def _get_api(self) -> MoooodotfarmAPI:
        return MetricsMoodotfarmAPI()


mod = Moooodotfarm
