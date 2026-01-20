import datetime
import os
import threading
from ...helpers import save_json, load_json, is_channel_name
from .. import BaseResponder, command
from ..lib import parse_command


def make_msg_entry(channel, message):
    """Creates an object stored by the message_store."""
    return {
        'channel': channel,
        'message': message,
        'time': datetime.datetime.utcnow().timestamp(),
    }


def format_msg_entry(nick, msg_entry):
    """Converts an object stored by the message store to plaintext."""
    time = datetime.datetime.fromtimestamp(msg_entry['time'])
    time = time.strftime('%Y-%m-%d %H:%MZ')
    return '%s was last seen on %s' % (nick, time)


class MessageStore(object):
    """Stores last messages sent by each user.

    path: function to call to get path to the data file.
    """

    def __init__(self, path):
        self.lock = threading.Lock()
        self.set_path(path)
        self._msg_store = {}
        self._load()

    def set_path(self, path):
        with self.lock:
            self._path = path

    def _load(self):
        if os.path.isfile(self._path()):
            try:
                self._msg_store = load_json(self._path())
            except:
                self._msg_store = {}

    def _save(self):
        save_json(self._path(), self._msg_store)

    def register_message(self, author, channel, message):
        with self.lock:
            self._msg_store[author] = make_msg_entry(channel, message)
            self._save()
        return True

    def get_message(self, author):
        with self.lock:
            return self._msg_store.get(author, None)


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

    def __init__(self, config):
        super().__init__(config)
        self.ms = MessageStore(lambda: self.config_get('message_data'))

    @command('seen')
    @parse_command([('nick', 1)])
    def command_seen(self, msg, auth, args):
        """Check when was the last time someone said something.

        Syntax: seen NICK
        """
        nick = args.nick[0]
        msg_entry = self.ms.get_message(nick)
        if msg_entry is not None:
            self.respond(msg, format_msg_entry(nick, msg_entry))
        else:
            self.respond(msg, 'I\'ve never seen %s' % args.nick[0])

    def handle_privmsg(self, msg):
        if is_channel_name(msg.params[0]):
            self.ms.register_message(msg.nickname, msg.params[0], msg.params[1])


mod = Seen
