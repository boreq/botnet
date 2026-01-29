import os
import re
import threading
from dataclasses import asdict
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
class PersistedMessage:
    author: str
    message: str


@dataclass()
class PersistedMessages:
    messages: dict[str, list[PersistedMessage]]


@dataclass()
class ParsedSedCommand:
    nick: str | None
    a: str
    b: str
    flags: list[str]


def parse_message(message_text: str) -> ParsedSedCommand | None:
    pattern = re.compile('^([^:, ]*)[:, ]*s/([^/]*)/([^/]*)(/|/[a-z]+)?$')
    result = pattern.search(message_text)
    if result is None:
        return None
    groups = list(result.groups())

    if groups[0] == '':
        nick = None
    else:
        nick = groups[0]

    if groups[3] is not None:
        flags = list(groups[3].lstrip('/'))
    else:
        flags = []

    return ParsedSedCommand(nick, groups[1], groups[2], flags)


def replace(messages: list[PersistedMessage], nick: str, a: str, b: str, flags: list[str]) -> str | None:
    for stored_msg in messages:
        print(stored_msg, nick, a, b, flags)
        if a in stored_msg.message and stored_msg.author == nick:
            if 'g' in flags:
                return stored_msg.message.replace(a, b)
            else:
                return stored_msg.message.replace(a, b, 1)
    return None


class MessageStore:
    _store: PersistedMessages

    def __init__(self, path_func: Callable[[], str], limit_func: Callable[[str], int]) -> None:
        self._lock = threading.Lock()
        self._path_func = path_func
        self._limit_func = limit_func
        self._load()

    def _load(self) -> None:
        p = self._path_func()
        if os.path.isfile(p):
            j = load_json(p)
            self._store = dacite.from_dict(data_class=PersistedMessages, data=j)

    def _save(self) -> None:
        save_json(self._path_func(), asdict(self._store))

    def add_message(self, channel: Channel, author: str, message: str) -> None:
        ch = channel.s.lower()
        with self._lock:
            if ch not in self._store.messages:
                self._store.messages[ch] = []
            msg_entry = PersistedMessage(author=author, message=message)
            self._store.messages[ch].insert(0, msg_entry)
            while len(self._store.messages[ch]) > self._limit_func(ch):
                self._store.messages[ch].pop()
            self._save()

    def get_messages(self, channel: Channel) -> list[PersistedMessage]:
        ch = channel.s.lower()
        with self._lock:
            if ch in self._store.messages:
                return list(self._store.messages[ch])
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
            parsed_message = parse_message(msg.text.s)
            if parsed_message is None:
                self.store.add_message(channel, msg.sender.s, msg.text.s)
                return

            if parsed_message.nick is not None:
                nick = parsed_message.nick
            else:
                nick = msg.sender.s

            messages = self.store.get_messages(channel)
            message = replace(messages, nick, parsed_message.a, parsed_message.b, parsed_message.flags)
            if message is not None:
                if Nick(nick) == msg.sender:
                    text = '%s meant to say: %s' % (nick, message)
                else:
                    text = '%s thinks %s meant to say: %s' % (msg.sender, nick, message)
                self.respond(msg, text)


mod = Sed
