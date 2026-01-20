import os
import threading
from typing import Any
from ...helpers import save_json, load_json, is_channel_name
from .. import BaseResponder, AuthContext, command
from ...message import Message
from ..decorators import predicates
from ..lib import parse_command


class NewsStore(object):

    def __init__(self, get_path):
        self._lock = threading.Lock()
        self._get_path = get_path
        self._news = {}
        self._load()

    def _load(self):
        if os.path.isfile(self._get_path()):
            try:
                self._news = load_json(self._get_path())
            except:
                self._news = {}

    def _save(self):
        save_json(self._get_path(), self._news)

    def push(self, channel, index, message):
        with self._lock:
            news = self._news.get(channel, [])
            news.insert(index, message)
            self._news[channel] = news
            self._save()

    def pop(self, channel, index):
        with self._lock:
            news = self._news.get(channel, [])
            news.pop(index)
            self._news[channel] = news
            self._save()

    def update(self, channel, index, message):
        with self._lock:
            news = self._news.get(channel, [])
            news[index] = message
            self._news[channel] = news
            self._save()

    def get(self, channel):
        with self._lock:
            return self._news.get(channel, []).copy()


def _is_enabled_for_this_channel():
    def predicate(module: Any, msg: Message, auth: AuthContext) -> bool:
        channel = msg.params[0] if is_channel_name(msg.params[0]) else None
        channels = module.config_get('channels', [])
        return channel in channels

    return predicates([predicate])


class News(BaseResponder):
    """Allows users to publish and read news.

    Example module config:

        "botnet": {
            "news": {
                "channels": ["#channel"],
                "news_data": "/path/to/news_data_file.json"
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'news'

    def __init__(self, config):
        super().__init__(config)
        self.store = NewsStore(lambda: self.config_get('news_data'))

    @command('news')
    @_is_enabled_for_this_channel()
    def command_news(self, auth, msg):
        """List news for the current channel.

        Syntax: news
        """
        channel = msg.params[0] if is_channel_name(msg.params[0]) else None
        channels = self.config_get('channels', [])
        if channel not in channels:
            return

        messages = self.store.get(channel)

        if not messages:
            self.respond(msg, 'There are no news.')

        for index, message in enumerate(messages):
            self.respond(msg, 'News {}: {}'.format(index, message))

    @command('news_add')
    @_is_enabled_for_this_channel()
    @parse_command([('message', '+')])
    def command_news_add(self, msg, auth, args):
        """Add a news entry for the current channel at the top of the list.

        Syntax: news_add MESSAGE
        """
        channel = msg.params[0] if is_channel_name(msg.params[0]) else None
        channels = self.config_get('channels', [])
        if channel not in channels:
            return

        self.store.push(channel, 0, ' '.join(args.message))
        self.respond(msg, 'Ok!')

    @command('news_push')
    @_is_enabled_for_this_channel()
    @parse_command([('index', 1), ('message', '+')])
    def command_news_push(self, msg, auth, args):
        """Add a news entry for the current channel.

        Syntax: news_push INDEX MESSAGE
        """
        channel = msg.params[0] if is_channel_name(msg.params[0]) else None
        channels = self.config_get('channels', [])
        if channel not in channels:
            return

        self.store.push(channel, int(args.index[0]), ' '.join(args.message))
        self.respond(msg, 'Ok!')

    @command('news_pop')
    @_is_enabled_for_this_channel()
    @parse_command([('index', 1)])
    def command_news_pop(self, msg, auth, args):
        """Remove a news entry for the current channel.

        Syntax: news_pop INDEX
        """
        channel = msg.params[0] if is_channel_name(msg.params[0]) else None
        channels = self.config_get('channels', [])
        if channel not in channels:
            return

        self.store.pop(channel, int(args.index[0]))
        self.respond(msg, 'Ok!')

    @command('news_update')
    @_is_enabled_for_this_channel()
    @parse_command([('index', 1), ('message', '+')])
    def command_news_update(self, msg, auth, args):
        """Update a news entry for the current channel.

        Syntax: news_update INDEX MESSAGE
        """
        channel = msg.params[0] if is_channel_name(msg.params[0]) else None
        channels = self.config_get('channels', [])
        if channel not in channels:
            return

        self.store.update(channel, int(args.index[0]), ' '.join(args.message))
        self.respond(msg, 'Ok!')


mod = News
