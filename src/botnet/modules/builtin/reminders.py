import datetime
import os
import threading
from ...helpers import save_json, load_json, is_channel_name
from ...signals import on_exception
from .. import BaseResponder, command, AuthContext
from ..lib import parse_command, Args
from ...message import Message
import re


def make_msg_entry(author, target, message, time):
    return {
        'author': author,
        'target': target,
        'message': message,
        'time': time,
        'set_on': datetime.datetime.utcnow().timestamp(),
    }


def format_msg_entry(msg_entry):
    time = datetime.datetime.fromtimestamp(msg_entry['set_on'])
    time = time.replace(microsecond=0).isoformat()
    return '%s: %s (set on %s)' % (msg_entry['author'], msg_entry['message'], time)


def get_amount_of_seconds(amount, unit):
    units = [
        [1, ['s', 'sec', 'second', 'seconds']],
        [60, ['m', 'min', 'mins', 'minute', 'minutes']],
        [60 * 60, ['h', 'hour', 'hours']],
        [60 * 60 * 24, ['d', 'day', 'days']],
        [60 * 60 * 24 * 30, ['month', 'months']],
        [60 * 60 * 24 * 365, ['y', 'year', 'years']],
    ]
    for u in units:
        if unit in u[1]:
            return amount * u[0]
    raise ValueError


def parse_message(message_text):
    parts = message_text.split()
    if len(parts) < 2:
        raise ValueError

    pattern = re.compile('^([0-9.]+)([a-z]*)$')
    result = pattern.search(parts[0])
    if result is None:
        raise ValueError
    groups = result.groups()

    amount = groups[0]
    unit = groups[1]
    parts = parts[1:]
    if not unit:
        if len(parts) < 2:
            raise ValueError
        unit = parts[0]
        parts = parts[1:]

    seconds = get_amount_of_seconds(float(amount), unit)
    return seconds, ' '.join(parts)


class RemindersStore:
    """RemindersStore saves the remiders in a data file.

    path: function to call to get path to the data file.
    """

    def __init__(self, path):
        self.lock = threading.Lock()
        self.set_path(path)
        self._store = []
        self._load()

    def set_path(self, path):
        with self.lock:
            self._path = path

    def _load(self):
        p = self._path()
        if os.path.isfile(p):
            try:
                self._store = load_json(p)
            except:
                self._store = []

    def _save(self):
        save_json(self._path(), self._store)

    def add_message(self, author, target, message, time):
        with self.lock:
            self._store.append(make_msg_entry(author, target, message, time))
            self._save()
        return True

    def get_messages(self, time):
        """Returns a list of messages with `time` smaller than the provided
        value.
        """
        entries = []
        with self.lock:
            for i, m in reversed(list(enumerate(self._store))):
                if m['time'] < time:
                    entries.append(self._store.pop(i))
            self._save()
        return list(reversed(entries))


class Reminders(BaseResponder):
    """Allows users to leave reminders.

    Example module config:

        "botnet": {
            "reminders": {
                "reminder_data": "/path/to/reminder_data_file.json"
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'reminders'
    deltatime = 1  # [s]

    def __init__(self, config):
        super().__init__(config)
        self.store = RemindersStore(lambda: self.config_get('reminder_data'))
        self.stop_event = threading.Event()
        self.t = threading.Thread(target=self.run)
        self.t.start()

    def stop(self):
        super().stop()
        self.stop_event.set()
        self.t.join()

    @command('in')
    @parse_command([('message', '+')])
    def command_in(self, msg: Message, auth: AuthContext, args: Args) -> None:
        """Set a reminder. Amount is a floating point number, unit is either
        seconds, minutes, hours, days or years. You will receive a message in
        the channel you created this reminder in or privately if you PM this
        command.

        Syntax: in AMOUNT UNIT MESSAGE
        """
        author = msg.nickname
        seconds, message = parse_message(' '.join(args.message))
        time = datetime.datetime.utcnow().timestamp() + seconds
        if not is_channel_name(msg.params[0]):
            target = msg.nickname
        else:
            target = msg.params[0]
        if self.store.add_message(author, target, message, time):
            self.respond(msg, 'Will do!')

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.update()
                self.stop_event.wait(self.deltatime)
            except Exception as e:
                on_exception.send(self, e=e)

    def update(self):
        now = datetime.datetime.utcnow().timestamp()
        for stored_msg in self.store.get_messages(now):
            target = stored_msg['target']
            text = format_msg_entry(stored_msg)
            self.message(target, text)


mod = Reminders
