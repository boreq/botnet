import datetime
import os
import threading
import dacite
from collections import namedtuple
from dataclasses import dataclass, asdict
from ...helpers import save_json, load_json, is_channel_name, cleanup_nick
from ...signals import message_out
from ...message import Message
from .. import BaseResponder
from ..lib import MemoryCache
from . import auth


DeferredAction = namedtuple('DeferredAction', ['channel', 'on_complete'])


class NamesMixin(object):
    """Provides a way of requesting and handling names that are in the channel."""

    cache_timeout = 60

    def __init__(self, config):
        super().__init__(config)
        self._cache = MemoryCache(self.cache_timeout)
        self._deferred = []
        self._current = {}

    def handler_rpl_namreply(self, msg):
        """Names reply."""
        channel = msg.params[2]
        if channel not in self._current:
            self._current[channel] = []
        self._current[channel].extend(msg.params[3].split(' '))

    def handler_rpl_endofnames(self, msg):
        """End of WHOIS."""
        if msg.params[1] not in self._current:
            return
        self._cache.set(msg.params[1], self._current.pop(msg.params[1]))
        self._run_deferred()

    def request_names(self, channel, on_complete):
        """Schedules an action to be completed when the names for the channel
        are available.

        channel: channel to query
        on_complete: function which will be called when the names will be
                     available. Required function signature:
                     void (*function)(list of nicks)
        """
        names = self._cache.get(channel)
        if names is not None:
            on_complete(names)
        else:
            data = DeferredAction(channel, on_complete)
            self._deferred.append(data)
            self._request(data.channel)

    def _run_deferred(self):
        """Loops over the deferred functions and launches those for which NAMES
        data is available.
        """
        for i in reversed(range(len(self._deferred))):
            d = self._deferred[i]
            data = self._cache.get(d.channel)
            if data is not None:
                self.logger.debug('Running deferred %s', d.on_complete)
                d.on_complete(data)
                self._deferred.pop(i)

    def _request(self, channel):
        """Sends a message with the NAMES command."""
        msg = Message(command='NAMES', params=[channel])
        message_out.send(self, msg=msg)

    def handle_msg(self, msg):
        # Dispatch to the handlers
        code = msg.command_code()
        if code is not None:
            handler_name = 'handler_%s' % code.name.lower()
        else:
            handler_name = 'handler_%s' % msg.command.lower()
        func = getattr(self, handler_name, None)
        if func is not None:
            func(msg)


class Gatekeep(NamesMixin, BaseResponder):
    """Allows users to see when was the last time someone said something.

    Example module config:

        "botnet": {
            "gatekeep": {
                "data": "/path/to/data_file.json",
                "channel": "#channel",
                "admin_group": "somegroup",
                "people": [
                    {
                        "nicks": [
                            "nick"
                        ],
                        "whitelist": true
                    }
                ]
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'gatekeep'

    def __init__(self, config):
        super().__init__(config)
        self.store = Store(lambda: self.config_get('data'))

    def handle_privmsg(self, msg):
        if is_channel_name(msg.params[0]) and msg.params[0] == self.config_get('channel'):
            self.store.on_privmsg(msg.nickname)

    def auth_command_gatekeep(self, msg, auth):
        authorised_group = self.config_get('authorised_group')
        if auth.group != authorised_group:
            return

        if is_channel_name(msg.params[0]):
            return

        def on_complete(names):
            names = [cleanup_nick(name) for name in names]
            print('names', names)

        self.request_names(self.config_get('channel'), on_complete)


class Store(object):

    def __init__(self, path):
        self.lock = threading.Lock()
        self.set_path(path)
        self._state = State({})
        self._load()

    def set_path(self, path):
        with self.lock:
            self._path = path

    def _load(self):
        if os.path.isfile(self._path()):
            try:
                j = load_json(self._path())
                self._state = dacite.from_dict(data_class=State, data=j)
            except:
                self._state = State({})

    def _save(self) -> None:
        save_json(self._path(), asdict(self._state))

    def on_privmsg(self, nick: str) -> None:
        with self.lock:
            self._state.on_privmsg(nick)
            self._save()


@dataclass
class State:
    message_info: dict[str, NickInfo]

    def on_privmsg(self, nick):
        if nick in self.message_info:
            self.message_info[nick].last_message = datetime.datetime.now().timestamp()
        else:
            self.message_info[nick] = NickInfo(datetime.datetime.now().timestamp(), datetime.datetime.now().timestamp(), [])


@dataclass
class NickInfo:
    first_message: float
    last_message: float
    endorsements: list[auth.Nick]


mod = Gatekeep
