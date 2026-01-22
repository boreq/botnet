import os
import threading
from typing import Callable
from ...helpers import save_json, load_json, is_channel_name
from .. import BaseResponder
from ...config import Config
from ...message import IncomingPrivateMessage
import re


def make_msg_entry(author: str, message: str) -> dict[str, str]:
    return {
        'author': author,
        'message': message,
    }


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


def replace(messages: list[dict[str, str]], nick: str, a: str, b: str, flags: list[str]) -> str | None:
    for stored_msg in messages:
        if a in stored_msg['message'] and stored_msg['author'] == nick:
            if 'g' in flags:
                return stored_msg['message'].replace(a, b)
            else:
                return stored_msg['message'].replace(a, b, 1)
    return None


class MessageStore:
    """MessageStore saves the past messages.

    limit: function to call to get the message limit for a specified channel.
    path: function to call to get path to the data file.
    """

    def __init__(self, path: Callable[[], str], limit: Callable[[str], int]) -> None:
        self.lock = threading.Lock()
        self.set_limit(limit)
        self.set_path(path)
        self._store: dict[str, list[dict[str, str]]] = {}
        self._load()

    def set_path(self, path: Callable[[], str]) -> None:
        with self.lock:
            self._path = path

    def set_limit(self, limit: Callable[[str], int]) -> None:
        with self.lock:
            self._limit = limit

    def _load(self) -> None:
        p = self._path()
        if os.path.isfile(p):
            try:
                self._store = load_json(p)
            except:
                self._store = {}

    def _save(self) -> None:
        save_json(self._path(), self._store)

    def add_message(self, channel: str, author: str, message: str) -> bool:
        with self.lock:
            if channel not in self._store:
                self._store[channel] = []
            self._store[channel].insert(0, make_msg_entry(author, message))
            while len(self._store[channel]) > self._limit(channel):
                self._store[channel].pop()
            self._save()
        return True

    def get_messages(self, channel: str) -> list[dict[str, str]]:
        """Returns a list of messages for the given channel."""
        with self.lock:
            if channel in self._store:
                return list(self._store[channel])
        return []


class Sed(BaseResponder):
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

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.store = MessageStore(lambda: self.config_get('message_data'), lambda c: self.config_get('message_limit', 100))

    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        if is_channel_name(msg.target):
            try:
                nick, a, b, flags = parse_message(msg.text)
                if nick is None:
                    nick = msg.sender
                messages = self.store.get_messages(msg.target)
                message = replace(messages, nick, a, b, flags)
                if message is not None:
                    if nick == msg.sender:
                        text = '%s meant to say: %s' % (nick, message)
                    else:
                        text = '%s thinks %s meant to say: %s' % (msg.sender, nick, message)
                    self.respond(msg, text)
            except ValueError:
                self.store.add_message(msg.target, msg.sender, msg.text)


mod = Sed
