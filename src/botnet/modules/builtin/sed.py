import os
import re
import threading
from dataclasses import dataclass
from typing import Callable

import dacite

from botnet.modules import privmsg_message_handler

from ...config import Config
from ...helpers import load_json
from ...helpers import save_json
from ...message import Channel
from ...message import IncomingPrivateMessage
from ...message import Nick
from .. import BaseResponder


@dataclass()
class MsgEntry:
    author: str
    message: str


def parse_message(message_text: str) -> tuple[str | None, str, str, list[str]]:
    pattern = re.compile('^([^:, ]*)[:, ]*s/([^/]*)/([^/]*)(/|/[a-z]+)?$')
    result = pattern.search(message_text)
    if result is None:
        raise ValueError
    groups = list(result.groups())

    # Nickname
    if groups[0] == '':
        groups[0] = None

    # Flags
    if groups[3] is not None:
        groups[3] = groups[3].lstrip('/')
    else:
        groups[3] = ''
    groups[3] = list(groups[3])

    return tuple(groups)  # type: ignore


def replace(messages: list[MsgEntry], nick: str, a: str, b: str, flags: list[str]) -> str | None:
    for stored_msg in messages:
        if a in stored_msg.message and stored_msg.author == nick:
            if 'g' in flags:
                return stored_msg.message.replace(a, b)
            else:
                return stored_msg.message.replace(a, b, 1)
    return None


class MessageStore:
    """MessageStore saves the past messages.

    limit: function to call to get the message limit for a specified channel.
    path: function to call to get path to the data file.
    """

    def __init__(self, path_func: Callable[[], str], limit_func: Callable[[str], int]) -> None:
        self.lock = threading.Lock()
        self._path_func = path_func
        self._limit_func = limit_func
        self._store: dict[str, list[MsgEntry]] = {}
        self._load()

    def _load(self) -> None:
        p = self._path_func()
        if os.path.isfile(p):
            j = load_json(p)
            self._store = {
                channel_name: [dacite.from_dict(data_class=MsgEntry, data=channel_message) for channel_message in channel_messages]
                for channel_name, channel_messages in j.items()
            }

    def _save(self) -> None:
        save_json(self._path_func(), self._store)

    def add_message(self, channel: Channel, author: str, message: str) -> bool:
        ch = channel.s.lower()
        with self.lock:
            if ch not in self._store:
                self._store[ch] = []
            msg_entry = MsgEntry(author=author, message=message)
            self._store[ch].insert(0, msg_entry)
            while len(self._store[ch]) > self._limit_func(ch):
                self._store[ch].pop()
            self._save()
        return True

    def get_messages(self, channel: Channel) -> list[MsgEntry]:
        """Returns a list of messages for the given channel."""
        ch = channel.s.lower()
        with self.lock:
            if ch in self._store:
                return list(self._store[ch])
        return []


@dataclass()
class SedConfig:
    message_data: str
    message_limit: int = 100


class Sed(BaseResponder[SedConfig]):
    """Allows users to use sed.

    Example module config:

        "botnet": {
            "sed": {
                "message_data": "/path/to/message_data_file.json"
                "message_limit": 100
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'sed'
    config_class = SedConfig

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.store = MessageStore(
            lambda: self.get_config().message_data,
            lambda c: self.get_config().message_limit,
        )

    @privmsg_message_handler()
    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        channel = msg.target.channel
        if channel is not None:
            try:
                nick, a, b, flags = parse_message(msg.text.s)
                if nick is None:
                    nick = msg.sender.s
                messages = self.store.get_messages(channel)
                message = replace(messages, nick, a, b, flags)
                if message is not None:
                    if Nick(nick) == msg.sender:
                        text = '%s meant to say: %s' % (nick, message)
                    else:
                        text = '%s thinks %s meant to say: %s' % (msg.sender, nick, message)
                    self.respond(msg, text)
            except ValueError:
                self.store.add_message(channel, msg.sender.s, msg.text.s)


mod = Sed
