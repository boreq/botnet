import dacite
import requests
from typing import Any, Protocol
from .. import BaseResponder, AuthContext
from ...message import IncomingPrivateMessage, Channel
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin


@dataclass
class Device:
    id: int
    name: str
    uniqueId: str  # the id you put in the app on your phone
    lastUpdate: datetime


@dataclass
class Position:
    id: int
    deviceId: int
    serverTime: datetime
    deviceTime: datetime
    fixTime: datetime
    latitude: float
    longitude: float
    altitude: float  # [meters]
    speed: float  # [knots]
    course: float  # [degrees]
    accuracy: float  # [meters]
    geofenceIds: None | list[int]
    attributes: dict[str, Any]


@dataclass
class Geofence:
    id: int
    name: str


_dacite_config = dacite.Config(type_hooks={
    datetime: datetime.fromisoformat
})


class TraccarAPI(Protocol):

    def devices(self) -> list[Device]:
        ...

    def positions(self) -> list[Position]:
        ...

    def geofences(self) -> list[Geofence]:
        ...


class RestTraccarAPI(TraccarAPI):

    def __init__(self, instance_url: str, token: str) -> None:
        self._instance_url = instance_url
        self._token = token

    def devices(self) -> list[Device]:
        response = self._get('/api/devices')
        return [
            dacite.from_dict(data_class=Device, data=item, config=_dacite_config)
            for item in response.json()
        ]

    def positions(self) -> list[Position]:
        response = self._get('/api/positions')
        return [
            dacite.from_dict(data_class=Position, data=item, config=_dacite_config)
            for item in response.json()
        ]

    def geofences(self) -> list[Geofence]:
        response = self._get('/api/geofences')
        return [
            dacite.from_dict(data_class=Geofence, data=item, config=_dacite_config)
            for item in response.json()
        ]

    def _get(self, path: str) -> requests.Response:
        response = requests.get(self._url(path), headers=self._headers())
        response.raise_for_status()
        return response

    def _url(self, path: str) -> str:
        return urljoin(self._instance_url, path)

    def _headers(self) -> dict[str, str]:
        return {
            'Authorization': f'Bearer {self._token}',
        }


class Traccar(BaseResponder):
    """Reports positions using traccar.

    Example module config:

        "botnet": {
            "traccar": {
                "instances": [
                    {
                        "url": "https://example.com"
                        "token": "yourtoken",
                        "location_commands": [
                            {
                                "command_names": ["whereissomeone"]
                                "channels": ["#channel"],
                                "device_name": "device-name",
                                "geofences": {
                                    "geofence-name": "Sanitized Name"
                                }
                            }
                        ],
                        "battery_commands": [
                            {
                                "command_names": ["whatissomeonesphonebatterypercentage"]
                                "channels": ["#channel"],
                                "device_name": "device-name"
                            }
                        ]
                    }
                ]
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'traccar'

    def get_all_commands(self, msg: IncomingPrivateMessage, auth: AuthContext) -> set[str]:
        rw = super().get_all_commands(msg, auth)
        channel = msg.target.channel
        if channel is not None:
            for instance in self.config_get('instances', []):
                for command_definition in instance['location_commands']:
                    if msg.target.channel in [Channel(v) for v in command_definition['channels']]:
                        for command in command_definition['command_names']:
                            rw.add(command)
                for command_definition in instance['battery_commands']:
                    if msg.target.channel in [Channel(v) for v in command_definition['channels']]:
                        for command in command_definition['command_names']:
                            rw.add(command)
        return rw

    def handle_auth_privmsg(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
        command_name = self.get_command_name(msg)
        if command_name is None:
            return

        channel = msg.target.channel
        if channel is not None:
            for instance_definition in self.config_get('instances', []):
                for location_command in instance_definition['location_commands']:
                    if command_name not in location_command['command_names']:
                        continue

                    if channel not in [Channel(v) for v in location_command['channels']]:
                        continue

                    try:
                        self._respond_with_location(
                            msg,
                            instance_definition['url'],
                            instance_definition['token'],
                            location_command['device_name'],
                            location_command['geofences'],
                        )
                    except ConnectionError:
                        self.respond(msg, 'Connection error.')

                for battery_command in instance_definition['battery_commands']:
                    if command_name not in battery_command['command_names']:
                        continue

                    if channel not in [Channel(v) for v in battery_command['channels']]:
                        continue

                    try:
                        self._respond_with_battery(
                            msg,
                            instance_definition['url'],
                            instance_definition['token'],
                            battery_command['device_name'],
                        )
                    except ConnectionError:
                        self.respond(msg, 'Connection error.')

    def _respond_with_location(self, msg: IncomingPrivateMessage, instance: str, token: str, device_name: str, sanitized_geofence_names: dict[str, str]) -> None:
        api = self._create_api(instance, token)

        device = self._find_device(api.devices(), device_name)
        if device is None:
            self.respond(msg, 'Device doesn\'t exist in the API response.')
            return

        position = self._find_position(api.positions(), device)
        if position is None:
            self.respond(msg, 'Position for the device doesn\'t exist in the API response.')
            return

        geofences = api.geofences()

        sanitized_geofences = []
        for geofence_id in position.geofenceIds if position.geofenceIds is not None else []:
            geofence = self._find_geofence(geofences, geofence_id)
            if geofence is not None:
                if geofence.name in sanitized_geofence_names:
                    sanitized_geofences.append(sanitized_geofence_names[geofence.name])

        if len(sanitized_geofences) == 0:
            if position.speed > 30:
                self.respond(msg, 'The eagle has left the nest and is moving at speed, over.')
                return

            self.respond(msg, 'The eagle has left the nest, over.')
            return

        self.respond(msg, 'Currently at: {} ({})'.format(', '.join(sanitized_geofences), self._confidence(position)))

    def _respond_with_battery(self, msg: IncomingPrivateMessage, instance: str, token: str, device_name: str) -> None:
        api = self._create_api(instance, token)

        device = self._find_device(api.devices(), device_name)
        if device is None:
            self.respond(msg, 'Device doesn\'t exist in the API response.')
            return

        position = self._find_position(api.positions(), device)
        if position is None:
            self.respond(msg, 'Position for the device doesn\'t exist in the API response.')
            return

        batteryLevel = position.attributes.get('batteryLevel', None)
        if batteryLevel is None:
            self.respond(msg, 'There is no battery level in the response from the server? Maybe this device sent no fixes yet?')
            return

        charging = ' (charging)' if position.attributes.get('charge', False) else ''
        self.respond(msg, f'{position.attributes['batteryLevel']}%{charging}')

    def _confidence(self, position: Position) -> str:
        if position.accuracy > 25:
            return 'maybe'

        if position.fixTime.timestamp() < datetime.now().timestamp() - 60 * 60 * 2:
            return 'probably'

        return 'confidence is high, I repeat, confidence is high'

    def _find_device(self, devices: list[Device], device_name: str) -> Device | None:
        for device in devices:
            if device_name == device.name:
                return device
        return None

    def _find_position(self, positions: list[Position], device: Device) -> Position | None:
        for position in positions:
            if position.deviceId == device.id:
                return position
        return None

    def _find_geofence(self, geofences: list[Geofence], geofence_id: int) -> Geofence | None:
        for geofence in geofences:
            if geofence.id == geofence_id:
                return geofence
        return None

    def _create_api(self, instance: str, token: str) -> TraccarAPI:
        return RestTraccarAPI(instance, token)


mod = Traccar
