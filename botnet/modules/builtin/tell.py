import datetime
import os
import threading
from ...helpers import save_json, load_json, is_channel_name
from .. import BaseResponder
from ..lib import parse_command


def make_msg_entry(author, target, message, channel):
    """Creates an object stored by the message_store."""
    return {
        'author': author,
        'target': target,
        'message': message,
        'channel': channel,
        'time': datetime.datetime.utcnow().timestamp(),
    }


def format_msg_entry(target, msg_entry):
    """Converts an object stored by the message store to plaintext."""
    time = datetime.datetime.fromtimestamp(msg_entry['time'])
    time = time.strftime('%H:%M')
    return '%s: %s <%s> %s' % (target, time, msg_entry['author'],
                               msg_entry['message'])


class MessageStore(object):
    """Simple facility for storing and saving messages left users, the messages
    are automatically saved in a file.

    path: function to call to get path to the data file.
    """

    def __init__(self, path):
        self.lock = threading.Lock()
        self.set_path(path)
        self._msg_store = []
        self._load()

    def set_path(self, path):
        with self.lock:
            self._path = path

    def _load(self):
        if os.path.isfile(self._path()):
            try:
                self._msg_store = load_json(self._path())
            except:
                self._msg_store = []

    def _save(self):
        save_json(self._path(), self._msg_store)

    def add_message(self, author, target, message, channel):
        """Leaves a `message` for `target` from `author`."""
        with self.lock:
            # abort if similar message already present
            for m in self._msg_store:
                if m['author'] == author \
                   and m['target'].lower() == target.lower() \
                   and m['channel'] == channel \
                   and m['message'] == message:
                    return False
            # add the new message
            self._msg_store.append(make_msg_entry(author, target, message, channel))
            self._save()
        return True

    def get_channel_messages(self, target, channel):
        """Returns a list of messages for `target`."""
        # This could be a generator to ensure that not all messages are lost in
        # case of an error.
        rw = []
        with self.lock:
            for i, m in reversed(list(enumerate(self._msg_store))):
                if m['target'].lower() == target.lower() and m['channel'].lower() == channel.lower():
                    rw.append(self._msg_store.pop(i))
            self._save()
        return list(reversed(rw))

    def get_private_messages(self, target):
        """Returns a list of messages for `target`."""
        # This could be a generator to ensure that not all messages are lost in
        # case of an error.
        rw = []
        with self.lock:
            for i, m in reversed(list(enumerate(self._msg_store))):
                if m['target'].lower() == target.lower() and m['channel'] is None:
                    rw.append(self._msg_store.pop(i))
            self._save()
        return list(reversed(rw))


class Tell(BaseResponder):
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

    def __init__(self, config):
        super().__init__(config)
        self.ms = MessageStore(lambda: self.config_get('message_data'))

    @parse_command([('target', 1), ('message', '+')], launch_invalid=False)
    def command_tell(self, msg, args):
        """Leave a message for someone. The user will receive the message the
        next time he sends anything in any of the channels.

        Syntax: tell TARGET MESSAGE
        """
        author = msg.nickname
        target = args.target[0]
        message = ' '.join(args.message)
        channel = msg.params[0] if is_channel_name(msg.params[0]) else None
        if self.ms.add_message(author, target, message, channel):
            self.respond(msg, 'Will do!')

    def handle_privmsg(self, msg):
        for stored_msg in self.ms.get_private_messages(msg.nickname):
            self.respond(msg, format_msg_entry(msg.nickname, stored_msg), pm=True)

        if is_channel_name(msg.params[0]):
            for stored_msg in self.ms.get_channel_messages(msg.nickname, msg.params[0]):
                self.respond(msg, format_msg_entry(msg.nickname, stored_msg))


mod = Tell
