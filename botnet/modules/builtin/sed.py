import os
import threading
from ...helpers import save_json, load_json, is_channel_name
from .. import BaseResponder
import re


def make_msg_entry(author, message):
    return {
        'author': author,
        'message': message,
    }


def parse_message(message_text):
    pattern = re.compile('^([^: ]*)[: ]*s/(.*)/(.*)$')
    result = pattern.search(message_text) 
    if result is None:
        raise ValueError
    groups = list(result.groups())
    if groups[0] == '':
        groups[0] = None
    return tuple(groups)


class MessageStore(object):
    """MessageStore saves the past messages.

    limit: function to call to get the message limit for a specified channel.
    path: function to call to get path to the data file.
    """

    def __init__(self, path, limit):
        self.lock = threading.Lock()
        self.set_limit(limit)
        self.set_path(path)
        self._store = {}
        self._load()

    def set_path(self, path):
        with self.lock:
            self._path = path

    def set_limit(self, limit):
        with self.lock:
            self._limit = limit

    def _load(self):
        p = self._path()
        if os.path.isfile(p):
            try:
                self._store = load_json(p)
            except:
                self._store = {}

    def _save(self):
        save_json(self._path(), self._store)

    def add_message(self, channel, author, message):
        with self.lock:
            if not channel in self._store:
                self._store[channel] = []
            self._store[channel].insert(0, make_msg_entry(author, message))
            while len(self._store[channel]) > self._limit(channel):
                self._store[channel].pop()
            self._save()
        return True

    def get_messages(self, channel):
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

    def __init__(self, config):
        super(Sed, self).__init__(config)
        self.store = MessageStore(lambda: self.config_get('message_data'), lambda c: self.config_get('message_limit', 100))

    def handle_privmsg(self, msg):
        if is_channel_name(msg.params[0]):
            try:
                nick, a, b = parse_message(' '.join(msg.params[1:]))
                if nick is None:
                    nick = msg.nickname
                for stored_msg in self.store.get_messages(msg.params[0]):
                    if a in stored_msg['message']:
                        message = stored_msg['message'].replace(a, b)
                        if nick == msg.nickname:
                            text = '%s meant to say: %s' % (nick, message)
                        else:
                            text = '%s thinks %s meant to say: %s' % (msg.nickname, nick, message)
                        self.respond(msg, text)
                        break
            except ValueError:
                self.store.add_message(msg.params[0], msg.nickname, ' '.join(msg.params[1:]))


mod = Sed
