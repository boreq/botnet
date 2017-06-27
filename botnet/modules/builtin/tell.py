import datetime
import os
import threading
from ...helpers import save_json, load_json
from .. import BaseResponder
from ..lib import parse_command

def make_msg_entry(author, target, message):
    """Creates an object stored by the message_store."""
    return {
        'author':author,
        'target': target,
        'message': message,
        'time': datetime.datetime.utcnow().timestamp(),
    }

def format_msg_entry(msg_entry):
    """Converts an object stored by the message store to plaintext."""
    time = datetime.datetime.fromtimestamp(msg_entry['time'])
    time = time.strftime('%H:%M')
    return '%s: %s <%s> %s' % (msg_entry['target'], time, msg_entry['author'],
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

    def add_message(self, author, target, message):
        """Leaves a `message` for `target` from `author`."""
        with self.lock:
            # abort if similar message already present
            for m in self._msg_store:
                if m['author'] == author \
                    and m['target'] == target \
                    and m['message'] == message:
                    return False
            # add the new message
            self._msg_store.append(make_msg_entry(author, target, message))
            self._save()
        return True

    def get_messages(self, target):
        """Returns a list of messages for `target`."""
        # This could be a generator to ensure that not all messages are lost in
        # case of an error.
        rw = []
        with self.lock:
            for i, m in reversed(list(enumerate(self._msg_store))):
                if m['target'].lower() == target.lower():
                    rw.append(self._msg_store.pop(i))
            self._save()
        return list(reversed(rw))


class Tell(BaseResponder):
    """Allows users to leave messages.
    
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
        super(Tell, self).__init__(config)
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
        if self.ms.add_message(author, target, message):
            self.respond(msg, 'Will do!')

    def handle_privmsg(self, msg):
        for stored_msg in self.ms.get_messages(msg.nickname):
            self.respond(msg, format_msg_entry(stored_msg))


mod = Tell
