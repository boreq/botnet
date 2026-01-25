import requests
from datetime import datetime
from botnet.modules.builtin.traccar import Traccar, TraccarAPI, Device, Position, Geofence
from botnet.message import Message
from botnet.config import Config
import pytest


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


def test_help_channel(make_privmsg, make_incoming_privmsg, unauthorised_context, test_traccar) -> None:
    msg = make_incoming_privmsg('.help', target='#channel')
    assert test_traccar.module.get_all_commands(msg, unauthorised_context) == {'help', 'whatissomeonesbatterylevel', 'whereissomeone'}


def test_help_direct(make_privmsg, make_incoming_privmsg, unauthorised_context, test_traccar) -> None:
    msg = make_incoming_privmsg('.help', target='bot_nick')
    assert test_traccar.module.get_all_commands(msg, unauthorised_context) == {'help'}


def test_in_geofence(make_privmsg, make_incoming_privmsg, unauthorised_context, test_traccar) -> None:
    mock_api: FakeTraccarAPI = test_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId=123, lastUpdate=datetime.now())
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

    msg = make_incoming_privmsg('.whereissomeone', target='#channel')
    test_traccar.receive_auth_message_in(msg, unauthorised_context)

    test_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Currently at: Nice Geofence Name (confidence is high, I repeat, confidence is high)')
            },
        ],
    )


def test_not_in_geofence(make_privmsg, make_incoming_privmsg, unauthorised_context, test_traccar) -> None:
    mock_api: FakeTraccarAPI = test_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId=123, lastUpdate=datetime.now())
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

    msg = make_incoming_privmsg('.whereissomeone', target='#channel')
    test_traccar.receive_auth_message_in(msg, unauthorised_context)

    test_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :The eagle has left the nest, over.')
            },
        ],
    )


def test_battery_not_available(make_privmsg, make_incoming_privmsg, unauthorised_context, test_traccar) -> None:
    mock_api: FakeTraccarAPI = test_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId=123, lastUpdate=datetime.now())
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

    msg = make_incoming_privmsg('.whatissomeonesbatterylevel', target='#channel')
    test_traccar.receive_auth_message_in(msg, unauthorised_context)

    test_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :There is no battery level in the response from the server? Maybe this device sent no fixes yet?')
            },
        ],
    )


def test_battery_charging(make_privmsg, make_incoming_privmsg, unauthorised_context, test_traccar) -> None:
    mock_api: FakeTraccarAPI = test_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId=123, lastUpdate=datetime.now())
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

    msg = make_incoming_privmsg('.whatissomeonesbatterylevel', target='#channel')
    test_traccar.receive_auth_message_in(msg, unauthorised_context)

    test_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :11% (charging)')
            },
        ],
    )


def test_battery_not_charging(make_privmsg, make_incoming_privmsg, unauthorised_context, test_traccar) -> None:
    mock_api: FakeTraccarAPI = test_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId=123, lastUpdate=datetime.now())
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

    msg = make_incoming_privmsg('.whatissomeonesbatterylevel', target='#channel')
    test_traccar.receive_auth_message_in(msg, unauthorised_context)

    test_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :11%')
            },
        ],
    )


def test_location_connection_error(make_privmsg, make_incoming_privmsg, unauthorised_context, test_traccar) -> None:
    mock_api: FakeTraccarAPI = test_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId=123, lastUpdate=datetime.now())
    ]

    mock_api.throw_on_positions = requests.ConnectionError('connection error')

    msg = make_incoming_privmsg('.whereissomeone', target='#channel')
    test_traccar.receive_auth_message_in(msg, unauthorised_context)

    test_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Connection error.')
            },
        ],
    )


def test_battery_connection_error(make_privmsg, make_incoming_privmsg, unauthorised_context, test_traccar) -> None:
    mock_api: FakeTraccarAPI = test_traccar.module.mock_api

    mock_api.mocked_devices = [
        Device(id=1, name='device-name', uniqueId=123, lastUpdate=datetime.now())
    ]

    mock_api.throw_on_positions = requests.ConnectionError('connection error')

    msg = make_incoming_privmsg('.whatissomeonesbatterylevel', target='#channel')
    test_traccar.receive_auth_message_in(msg, unauthorised_context)

    test_traccar.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Connection error.')
            },
        ],
    )


@pytest.fixture()
def test_traccar(module_harness_factory):
    class TestTraccar(Traccar):
        mock_api = FakeTraccarAPI()

        def _create_api(self, url: str, token: str) -> TraccarAPI:
            assert url == 'https://example.com'
            assert token == 'some-token'
            return self.mock_api

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

    return module_harness_factory.make(TestTraccar, config)
