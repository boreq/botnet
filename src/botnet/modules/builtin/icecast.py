import threading
from dataclasses import dataclass
from enum import Enum

import requests

from ...config import Config
from ...message import Target
from ...signals import on_exception
from .. import BaseResponder

_CHECK_INTERVAL_SECONDS = 30


class StreamStatus(Enum):
    ONLINE = 'ONLINE'
    OFFLINE = 'OFFLINE'


@dataclass()
class IcecastConfig:
    url: str
    channels: list[str]
    message: str


class Icecast(BaseResponder[IcecastConfig]):
    """Periodically checks an Icecast status endpoint and announces when a
    stream goes online.

    Example module config:

        "botnet": {
            "icecast": {
                "url": "https://example.com/status-json.xsl",
                "channels": ["#channel"],
                "message": "Stream is now live! Tune in at https://example.com"
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'icecast'
    config_class = IcecastConfig

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._status = StreamStatus.OFFLINE
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def stop(self) -> None:
        super().stop()
        self._stop_event.set()
        self._thread.join()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._check()
            except Exception as e:
                on_exception.send(self, e=e)
            self._stop_event.wait(_CHECK_INTERVAL_SECONDS)

    def _check(self) -> None:
        config = self.get_config()

        try:
            response = requests.get(config.url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            return

        source_present = 'source' in data.get('icestats', {})
        new_status = StreamStatus.ONLINE if source_present else StreamStatus.OFFLINE

        if new_status == StreamStatus.ONLINE and self._status == StreamStatus.OFFLINE:
            for channel in config.channels:
                self.message(Target.new_from_string(channel), config.message)

        self._status = new_status


mod = Icecast
