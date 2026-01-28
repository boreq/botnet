import datetime
import os
import threading
from dataclasses import dataclass
from typing import Callable

import dacite

from ...config import Config
from ...helpers import load_json
from ...helpers import save_json
from ...message import Channel
from ...message import IncomingPrivateMessage
from ...message import Nick
from ...message import Text
from .. import Args
from .. import AuthContext
from .. import BaseResponder
from .. import command
from .. import parse_command
from .. import privmsg_message_handler


@dataclass()
class MsgEntry:
    channel: str
    message: str
    time: float


def format_msg_entry(nick: Nick, msg_entry: MsgEntry) -> str:
    """Converts an object stored by the message store to plaintext."""
    time = datetime.datetime.fromtimestamp(msg_entry.time, datetime.timezone.utc)
    time_str = time.strftime('%Y-%m-%d %H:%MZ')
    return '%s was last seen on %s' % (nick, time_str)


class MessageStore:
    """Stores last messages sent by each user.

    path: function to call to get path to the data file.
    now_func: function returning current datetime (used for testing).
    """

    def __init__(self, path_func: Callable[[], str], now_func: Callable[[], datetime.datetime] | None = None) -> None:
        self.lock = threading.Lock()
        self._path_func = path_func
        self._now_func = now_func or (lambda: datetime.datetime.now(datetime.timezone.utc))
        self._msg_store: dict[str, MsgEntry] = {}
        self._load()

    def register_message(self, author: Nick, channel: Channel, message: Text) -> bool:
        with self.lock:
            self._msg_store[author.s.lower()] = self._make_msg_entry(channel, message, self._now_func())
            self._save()
        return True

    def get_message(self, author: Nick) -> MsgEntry | None:
        with self.lock:
            return self._msg_store.get(author.s.lower(), None)

    def _load(self) -> None:
        if os.path.isfile(self._path_func()):
            j = load_json(self._path_func())
            self._msg_store = {
                key: dacite.from_dict(data_class=MsgEntry, data=value)
                for key, value in j.items()
            }

    def _save(self) -> None:
        save_json(self._path_func(), self._msg_store)

    def _make_msg_entry(self, channel: Channel, message: Text, now: datetime.datetime) -> MsgEntry:
        return MsgEntry(
            channel=channel.s.lower(),
            message=message.s,
            time=now.timestamp(),
        )


@dataclass
class SeenConfig:
    message_data: str


class Seen(BaseResponder[SeenConfig]):
    """Allows users to see when was the last time someone said something.

    Example module config:

        "botnet": {
            "seen": {
                "message_data": "/path/to/message_data_file.json"
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'seen'
    config_class = SeenConfig

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.ms = MessageStore(lambda: self.get_config().message_data, now_func=self._now)

    @command('seen')
    @parse_command([('nick', 1)])
    def command_seen(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Check when was the last time someone said something.

        Syntax: seen NICK
        """
        nick = Nick(args['nick'][0])
        msg_entry = self.ms.get_message(nick)
        if msg_entry is not None:
            self.respond(msg, format_msg_entry(nick, msg_entry))
        else:
            self.respond(msg, 'I\'ve never seen %s' % nick)

    @privmsg_message_handler()
    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        channel = msg.target.channel
        if channel is not None:
            self.ms.register_message(msg.sender, channel, msg.text)

    def _now(self) -> datetime.datetime:
        """Return current datetime in UTC. Tests may override this."""
        return datetime.datetime.now(datetime.timezone.utc)


mod = Seen
