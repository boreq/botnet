from datetime import datetime

import pytest
import requests

from botnet.config import Config
from botnet.message import Channel
from botnet.message import IncomingPrivateMessage
from botnet.message import Message
from botnet.message import Nick
from botnet.message import Target
from botnet.message import Text
from botnet.modules import AuthContext
from botnet.modules.builtin.traccar import Device
from botnet.modules.builtin.traccar import Geofence
from botnet.modules.builtin.traccar import Position
from botnet.modules.builtin.traccar import Traccar
from botnet.modules.builtin.traccar import TraccarAPI

from ...conftest import MakePrivmsgFixture
from ...conftest import ModuleHarness
from ...conftest import ModuleHarnessFactory


class FakeTraccarAPI(TraccarAPI):
    mocked_devices: list[Device] = []
    mocked_positions: list[Position] = []
    mocked_geofences: list[Geofence] = []
    throw_on_devices: Exception | None = None
    throw_on_positions: Exception | None = None
    throw_on_geofences: Exception | None = None

    def devices(self) -> list[Device]:
        if self.throw_on_devices is not None:
            raise self.throw_on_devices
        return self.mocked_devices

    def positions(self) -> list[Position]:
        if self.throw_on_positions is not None:
            raise self.throw_on_positions
        return self.mocked_positions

    def geofences(self) -> list[Geofence]:
        if self.throw_on_geofences is not None:
            raise self.throw_on_geofences
        return self.mocked_geofences


class TraccarForTest(Traccar):
    mock_api = FakeTraccarAPI()

    def _create_api(self, url: str, token: str) -> TraccarAPI:
        assert url == 'https://example.com'
        assert token == 'some-token'
        return self.mock_api


def test_help_channel(unauthorised_context: AuthContext, tested_traccar: ModuleHarness[TraccarForTest]) -> None:
    msg = IncomingPrivateMessage(
        sender=Nick('nick'),
        target=Target(Channel('#channel')),
        text=Text('.help')
    )
    assert tested_traccar.module.get_all_commands(msg, unauthorised_context) == {'help', 'whatissomeonesbatterylevel', 'whereissomeone'}


def test_help_direct(unauthorised_context: AuthContext, tested_traccar: ModuleHarness[TraccarForTest]) -> None:
    msg = IncomingPrivateMessage(
        sender=Nick('nick'),
        target=Target(Nick('bot_nick')),
        text=Text('.help')
    )
    assert tested_traccar.module.get_all_commands(msg, unauthorised_context) == {'help'}


def test_in_geofence(make_privmsg: MakePrivmsgFixture, tested_traccar: ModuleHarness[TraccarForTest]) -> None:
    mock_api = tested_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId='123', lastUpdate=datetime.now())
    ]

    mock_api.mocked_positions = [
        Position(
            id=1,
            deviceId=1,
            serverTime=datetime.now(),
            deviceTime=datetime.now(),
            fixTime=datetime.now(),
            latitude=10,
            longitude=20,
            altitude=10,
            speed=10,
            course=180,
            accuracy=10,
            geofenceIds=[1],
            attributes={},
        )
    ]

    mock_api.mocked_geofences = [
        Geofence(
            id=1,
            name='geofence-name',
        )
    ]

    msg = make_privmsg('.whereissomeone', target='#channel')
    tested_traccar.receive_message_in(msg)

    tested_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Currently at: Nice Geofence Name (confidence is high, I repeat, confidence is high)')
            },
        ],
    )


def test_not_in_geofence(make_privmsg: MakePrivmsgFixture, tested_traccar: ModuleHarness[TraccarForTest]) -> None:
    mock_api = tested_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId='123', lastUpdate=datetime.now())
    ]

    mock_api.mocked_positions = [
        Position(
            id=1,
            deviceId=1,
            serverTime=datetime.now(),
            deviceTime=datetime.now(),
            fixTime=datetime.now(),
            latitude=10,
            longitude=20,
            altitude=10,
            speed=10,
            course=180,
            accuracy=10,
            geofenceIds=[],
            attributes={},
        )
    ]

    mock_api.mocked_geofences = [
        Geofence(
            id=1,
            name='geofence-name',
        )
    ]

    msg = make_privmsg('.whereissomeone', target='#channel')
    tested_traccar.receive_message_in(msg)

    tested_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :The eagle has left the nest, over.')
            },
        ],
    )


def test_battery_not_available(make_privmsg: MakePrivmsgFixture, tested_traccar: ModuleHarness[TraccarForTest]) -> None:
    mock_api = tested_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId='123', lastUpdate=datetime.now())
    ]

    mock_api.mocked_positions = [
        Position(
            id=1,
            deviceId=1,
            serverTime=datetime.now(),
            deviceTime=datetime.now(),
            fixTime=datetime.now(),
            latitude=10,
            longitude=20,
            altitude=10,
            speed=10,
            course=180,
            accuracy=10,
            geofenceIds=[],
            attributes={},
        )
    ]

    msg = make_privmsg('.whatissomeonesbatterylevel', target='#channel')
    tested_traccar.receive_message_in(msg)

    tested_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :There is no battery level in the response from the server? Maybe this device sent no fixes yet?')
            },
        ],
    )


def test_battery_charging(make_privmsg: MakePrivmsgFixture, tested_traccar: ModuleHarness[TraccarForTest]) -> None:
    mock_api = tested_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId='123', lastUpdate=datetime.now())
    ]

    mock_api.mocked_positions = [
        Position(
            id=1,
            deviceId=1,
            serverTime=datetime.now(),
            deviceTime=datetime.now(),
            fixTime=datetime.now(),
            latitude=10,
            longitude=20,
            altitude=10,
            speed=10,
            course=180,
            accuracy=10,
            geofenceIds=[],
            attributes={
                'batteryLevel': 11,
                'charge': True,
            },
        )
    ]

    msg = make_privmsg('.whatissomeonesbatterylevel', target='#channel')
    tested_traccar.receive_message_in(msg)

    tested_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :11% (charging)')
            },
        ],
    )


def test_battery_not_charging(make_privmsg: MakePrivmsgFixture, tested_traccar: ModuleHarness[TraccarForTest]) -> None:
    mock_api = tested_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId='123', lastUpdate=datetime.now())
    ]

    mock_api.mocked_positions = [
        Position(
            id=1,
            deviceId=1,
            serverTime=datetime.now(),
            deviceTime=datetime.now(),
            fixTime=datetime.now(),
            latitude=10,
            longitude=20,
            altitude=10,
            speed=10,
            course=180,
            accuracy=10,
            geofenceIds=[],
            attributes={
                'batteryLevel': 11,
            },
        )
    ]

    msg = make_privmsg('.whatissomeonesbatterylevel', target='#channel')
    tested_traccar.receive_message_in(msg)

    tested_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :11%')
            },
        ],
    )


def test_location_connection_error(make_privmsg: MakePrivmsgFixture, tested_traccar: ModuleHarness[TraccarForTest]) -> None:
    mock_api = tested_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId='123', lastUpdate=datetime.now())
    ]

    mock_api.throw_on_positions = requests.ConnectionError('connection error')

    msg = make_privmsg('.whereissomeone', target='#channel')
    tested_traccar.receive_message_in(msg)

    tested_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Connection error.')
            },
        ],
    )


def test_battery_connection_error(make_privmsg: MakePrivmsgFixture, tested_traccar: ModuleHarness[TraccarForTest]) -> None:
    mock_api = tested_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId='123', lastUpdate=datetime.now())
    ]

    mock_api.throw_on_positions = requests.ConnectionError('connection error')

    msg = make_privmsg('.whatissomeonesbatterylevel', target='#channel')
    tested_traccar.receive_message_in(msg)

    tested_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Connection error.')
            },
        ],
    )


@pytest.fixture()
def tested_traccar(module_harness_factory: ModuleHarnessFactory) -> ModuleHarness[TraccarForTest]:
    config = Config(
        {
            'module_config': {
                'botnet': {
                    'traccar': {
                        'instances': [
                            {
                                'url': 'https://example.com',
                                'token': 'some-token',
                                'location_commands': [
                                    {
                                        'command_names': ['whereissomeone'],
                                        'channels': ['#channel'],
                                        'device_name': 'device-name',
                                        'geofences': {
                                            'geofence-name': 'Nice Geofence Name'
                                        },
                                    }
                                ],
                                'battery_commands': [
                                    {
                                        'command_names': ['whatissomeonesbatterylevel'],
                                        'channels': ['#channel'],
                                        'device_name': 'device-name',
                                    }
                                ],
                            },
                        ]
                    },
                },
            },
        }
    )

    return module_harness_factory.make(TraccarForTest, config)
