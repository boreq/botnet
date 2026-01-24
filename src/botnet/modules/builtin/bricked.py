from .. import BaseResponder, AuthContext
from ...message import IncomingPrivateMessage, Channel
import requests
import dacite
from dataclasses import dataclass
from urllib.parse import urljoin


@dataclass
class Status:
    status: float


class BrickedAPI:
    def get_status(self, id: str) -> Status:
        raise NotImplementedError


class RestBrickedAPI(BrickedAPI):
    def __init__(self, instance_url: str) -> None:
        self._instance_url = instance_url

    def get_status(self, id: str) -> Status:
        r = self._get(f'/api/status/{id}')
        j = r.json()
        return dacite.from_dict(data_class=Status, data=j)

    def _get(self, path: str) -> requests.Response:
        r = requests.get(self._url(path))
        r.raise_for_status()
        return r

    def _url(self, path: str) -> str:
        return urljoin(self._instance_url, path)


class Bricked(BaseResponder):
    """Reports statuses.

    Example module config:

        "botnet": {
            "bricked": {
                "statuses": [
                    {
                        "commands": ["status"],
                        "channels": ["#channel"],
                        "instance": "https://example.com",
                        "id": "person_id"
                    }
                ]
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'bricked'

    def get_all_commands(self, msg: IncomingPrivateMessage, auth: AuthContext) -> set[str]:
        rw = super().get_all_commands(msg, auth)
        channel = msg.target.channel
        if channel is not None:
            for entry in self.config_get('statuses', []):
                if channel in [Channel(str) for str in entry['channels']]:
                    for command in entry['commands']:
                        rw.add(command)
        return rw

    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        command_name = self.get_command_name(msg)
        if command_name is None:
            return

        channel = msg.target.channel
        if channel is not None:
            for entry in self.config_get('statuses', []):
                if command_name not in entry['commands']:
                    continue

                if channel.s.lower() not in entry['channels']:
                    continue

                api = self._create_api(entry['instance'])
                status = api.get_status(entry['id'])
                self.respond(msg, '{:.0f}%'.format(status.status * 100))

    def _create_api(self, instance: str) -> BrickedAPI:
        return RestBrickedAPI(instance)


mod = Bricked
