from dataclasses import dataclass
from datetime import datetime, timezone
import os
import threading
from typing import Callable
from ...helpers import save_json, load_json
from .. import BaseResponder, command, AuthContext, parse_command, Args
from ...config import Config
from ...message import IncomingPrivateMessage, Nick, Target, Channel


def make_msg_entry(author: str, target: str, message: str, channel: str | None, time: datetime) -> dict:
    """Creates an object stored by the message_store."""
    return {
        'author': author,
        'target': target,
        'message': message,
        'channel': channel,
        'time': time.timestamp(),
    }


def format_msg_entry(target: Nick, msg_entry: dict) -> str:
    """Converts an object stored by the message store to plaintext."""
    dt = datetime.fromtimestamp(msg_entry['time'], timezone.utc)
    return '%s: %s <%s> %s' % (target,
                               dt.strftime('%Y-%m-%d %H:%M:%SZ'),
                               msg_entry['author'],
                               msg_entry['message'])


class MessageStore:
    """Simple facility for storing and saving messages left users, the messages
    are automatically saved in a file.

    path: function to call to get path to the data file.
    """

    def __init__(self, path: Callable[[], str]) -> None:
        self._lock = threading.Lock()
        self._path = path
        self._msg_store: list[dict] = []
        self._load()

    def add_message(self, author: Nick, target: Target, message: str, channel: Channel | None, time: datetime) -> bool:
        """Leaves a `message` for `target` from `author`."""
        with self._lock:
            # abort if similar message already present
            for m in self._msg_store:
                if Nick(m['author']) == author \
                   and Target.new_from_string(m['target']) == target \
                   and Channel(m['channel']) == channel \
                   and m['message'] == message:
                    return False
            # add the new message
            self._msg_store.append(make_msg_entry(author.s, target.nick_or_channel.s, message, channel.s if channel is not None else None, time))
            self._save()
        return True

    def get_channel_messages(self, target: Nick, channel: Channel) -> list[dict]:
        """Returns a list of messages for `target`."""
        # This could be a generator to ensure that not all messages are lost in
        # case of an error.
        rw = []
        with self._lock:
            for i, m in reversed(list(enumerate(self._msg_store))):
                if m['target'].lower() == target.s.lower() and m['channel'].lower() == channel.s.lower():
                    rw.append(self._msg_store.pop(i))
            self._save()
        return list(reversed(rw))

    def get_private_messages(self, target: Nick) -> list[dict]:
        """Returns a list of messages for `target`."""
        # This could be a generator to ensure that not all messages are lost in
        # case of an error.
        rw = []
        with self._lock:
            for i, m in reversed(list(enumerate(self._msg_store))):
                if m['target'].lower() == target.s.lower() and m['channel'] is None:
                    rw.append(self._msg_store.pop(i))
            self._save()
        return list(reversed(rw))

    def _load(self) -> None:
        if os.path.isfile(self._path()):
            try:
                self._msg_store = load_json(self._path())
            except:
                self._msg_store = []

    def _save(self) -> None:
        save_json(self._path(), self._msg_store)


@dataclass()
class TellConfig:
    message_data: str


class Tell(BaseResponder[TellConfig]):
    """Allows users to leave messages for each other. If this command is
    executed in a channel then the bot will pass on the message in the same
    channel. If this command is sent in a privmsg then a bot will pass on the
    message in a privmsg once the target user sends a message in one of the
    channel the bot is in.

    Example module config:

        "botnet": {
            "tell": {
                "message_data": "/path/to/message_data_file.json"
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'tell'
    config_class = TellConfig

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.ms = MessageStore(lambda: self.get_config().message_data)

    @command('tell')
    @parse_command([('target', 1), ('message', '+')])
    def command_tell(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Leave a message for someone. The user will receive the message the
        next time he sends anything in any of the channels.

        Syntax: tell TARGET MESSAGE
        """
        author = msg.sender
        target = Target.new_from_string(args['target'][0])
        message = ' '.join(args['message'])
        channel = msg.target.channel
        time = self.now()
        if self.ms.add_message(author, target, message, channel, time):
            self.respond(msg, 'Will do!')

    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        for stored_msg in self.ms.get_private_messages(msg.sender):
            self.respond(msg, format_msg_entry(msg.sender, stored_msg), pm=True)

        channel = msg.target.channel
        if channel is not None:
            for stored_msg in self.ms.get_channel_messages(msg.sender, channel):
                self.respond(msg, format_msg_entry(msg.sender, stored_msg))

    def now(self) -> datetime:
        return datetime.now()


mod = Tell
