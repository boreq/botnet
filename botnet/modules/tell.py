import datetime
from threading import Lock
from . import BaseResponder, parse_command
from ..helpers import load_json, save_json
from ..logging import get_logger


class MessageStore(list):
    """Used for storing messages which should be passed to the users."""

    def __init__(self, file_path, *args, **kwargs):
        super(MessageStore, self).__init__(*args, **kwargs)
        self.logger = get_logger(self)
        self.file_path = file_path
        self.lock = Lock()
        self.messages = {}

    def load(self):
        """Loads messages from the data file."""
        try:
            self.messages = load_json(self.file_path)
        except FileNotFoundError as e:
            self.logger.warning(str(e))

    def save(self):
        """Saves messages to the data file."""
        save_json(self.file_path, self.messages)

    def add(self, recipient, sender, text):
        """Adds a message to an interal list. It is recommened to run self.save
        after doing that.
        """
        if not self.exists(recipient, sender, text):
            if not recipient in self.messages:
                self.messages[recipient] = []
            data = {
                'sender': sender,
                'text': text,
                'time': datetime.datetime.utcnow().isoformat()
            }
            self.messages[recipient].append(data)
            return True
        return False

    def exists(self, recipient, sender, text):
        """Checks if an identical message already exists."""
        if recipient in self.messages:
            for stored_msg in self.messages[recipient]:
                if stored_msg['sender'] == sender and stored_msg['text'] == text:
                    return True
        return False


class Tell(BaseResponder):
    """Allows to leave messages for offline users.

    Example config:

        "tell": {
            "data_file": "/path/to/data.json"
        }

    """

    def __init__(self, config):
        super(Tell, self).__init__(config)
        self.config = config.get_for_module('tell')
        self.msg_st = MessageStore(self.config['data_file'])
        with self.msg_st.lock:
            self.msg_st.load()

    @parse_command([('recipient', 1), ('message', '+')], launch_invalid=False)
    def command_tell(self, msg, args):
        """Sends a message to a RECIPIENT when he is available.

        tell RECIPIENT MESSAGE
        """
        text = ' '.join(args.message)
        with self.msg_st.lock:
            added = self.msg_st.add(args.recipient[0], msg.nickname, text)
            if added:
                self.msg_st.save()
        if added:
            self.respond(msg, 'Will do, %s.' % msg.nickname)

    def handle_message(self, msg):
        """When a user writes a message in a channel send him all stored
        messages.
        """
        with self.msg_st.lock:
            messages = self.msg_st.messages.pop(msg.nickname, [])
            self.msg_st.save()
        for m in messages:
            text = '%s: <%s> %s' % (msg.nickname, m['sender'], m['text'])
            self.respond(msg, text)


mod = Tell
