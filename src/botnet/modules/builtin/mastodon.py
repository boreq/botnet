from dataclasses import dataclass
from typing import Protocol

from mastodon import Mastodon as MastodonLib

from botnet.modules import privmsg_message_handler

from ...message import Channel
from ...message import IncomingPrivateMessage
from .. import AuthContext
from .. import BaseResponder


@dataclass
class Toot:
    url: str


class MastodonAPI(Protocol):
    def toot(self, text: str) -> Toot:
        ...


class RestMastodonAPI:
    def __init__(self, instance: str, access_token: str) -> None:
        self._instance = instance
        self._access_token = access_token

    def toot(self, text: str) -> Toot:
        mastodon = MastodonLib(access_token=self._access_token, api_base_url=self._instance)
        status = mastodon.toot(text)
        return Toot(url=getattr(status, 'url', str(status)))


@dataclass()
class MastodonConfig:
    tooting: list[MastodonConfigTooting]


@dataclass()
class MastodonConfigTooting:
    command: str
    channels: list[str]
    instance: str
    access_token: str


class Mastodon(BaseResponder[MastodonConfig]):
    """Lets you toot.

    Example module config:

        "botnet": {
            "mastodon": {
                "tooting": [
                    {
                        "command": "toot",
                        "channels": ["#channel"],
                        "instance": "https://example.com",
                        "access_token": "token"
                    }
                ]
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'mastodon'
    config_class = MastodonConfig

    max_toot_len = 250

    def get_all_commands(self, msg: IncomingPrivateMessage, auth: AuthContext) -> set[str]:
        rw = super().get_all_commands(msg, auth)
        channel = msg.target.channel
        if channel is not None:
            config = self.get_config()
            for entry in config.tooting:
                if channel in [Channel(s) for s in entry.channels]:
                    rw.add(entry.command)
        return rw

    @privmsg_message_handler()
    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        command_name = self.get_command_name(msg)
        if command_name is None:
            return

        channel = msg.target.channel
        if channel is None:
            return

        config = self.get_config()

        for entry in config.tooting:
            if entry.command != command_name:
                continue

            if channel not in [Channel(s) for s in entry.channels]:
                continue

            parts = msg.text.s.split(" ", 1)
            text = parts[1].strip()
            if len(text) > self.max_toot_len:
                return

            api = self._create_api(entry.instance, entry.access_token)
            toot = api.toot(text)
            self.respond(msg, toot.url)

    def _create_api(self, instance: str, access_token: str) -> MastodonAPI:
        return RestMastodonAPI(instance, access_token)


mod = Mastodon
