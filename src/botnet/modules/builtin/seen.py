import datetime
import os
import threading
from typing import Any, Callable
from ...helpers import save_json, load_json
from .. import BaseResponder, command, AuthContext, parse_command, Args
from ...message import IncomingPrivateMessage, Nick, Channel, Text
from ...config import Config


def make_msg_entry(channel: str, message: str) -> dict[str, Any]:
    """Creates an object stored by the message_store."""
    return {
        'channel': channel,
        'message': message,
        'time': datetime.datetime.utcnow().timestamp(),
    }


def format_msg_entry(nick: Nick, msg_entry: dict[str, Any]) -> str:
    """Converts an object stored by the message store to plaintext."""
    time = datetime.datetime.fromtimestamp(msg_entry['time'])
    time_str = time.strftime('%Y-%m-%d %H:%MZ')
    return '%s was last seen on %s' % (nick, time_str)


class MessageStore:
    """Stores last messages sent by each user.

    path: function to call to get path to the data file.
    """

    def __init__(self, path: Callable[[], str]) -> None:
        self.lock = threading.Lock()
        self.set_path(path)
        self._msg_store: dict[str, dict[str, Any]] = {}
        self._load()

    def set_path(self, path: Callable[[], str]) -> None:
        with self.lock:
            self._path = path

    def _load(self) -> None:
        if os.path.isfile(self._path()):
            try:
                self._msg_store = load_json(self._path())
            except:
                self._msg_store = {}

    def _save(self) -> None:
        save_json(self._path(), self._msg_store)

    def register_message(self, author: Nick, channel: Channel, message: Text) -> bool:
        with self.lock:
            self._msg_store[author.s.lower()] = make_msg_entry(channel.s.lower(), message.s)
            self._save()
        return True

    def get_message(self, author: Nick) -> dict[str, Any] | None:
        with self.lock:
            return self._msg_store.get(author.s.lower(), None)


class Seen(BaseResponder):
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

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.ms = MessageStore(lambda: self.config_get('message_data'))

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

    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        channel = msg.target.channel
        if channel is not None:
            self.ms.register_message(msg.sender, channel, msg.text)


mod = Seen
