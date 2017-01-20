import threading
import requests
import json
from requests_oauthlib import OAuth1
from typing import List, Iterator, Any
from .. import BaseResponder
from ...signals import on_exception, message_out, config_reloaded
from ...message import Message


class API(object):
    """Unfortunately *ALL* Python Twitter libraries are literally broken, as in
    written in a way that is simply wrong and makes it impossible to close the
    connection in a clean way. It is not some kind of a purity problem, the code
    written in those libraries is simply invalid.
    """

    stream_url = 'https://stream.twitter.com/1.1'

    def __init__(self, consumer_key: str, consumer_secret: str,
                 access_token_key: str, access_token_secret: str,
                 follow: List[str]) -> None:
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._access_token_key = access_token_key
        self._access_token_secret = access_token_secret
        self._response = self._stream_filter(follow)

    def _stream_filter(self, follow: List[str]) -> requests.Response:
        url = '%s/statuses/filter.json' % self.stream_url
        data = {
            'follow': ','.join(follow),
            'stall_warnings': 'true',
        }
        auth = OAuth1(self._consumer_key, self._consumer_secret,
                      self._access_token_key, self._access_token_secret)
        return requests.post(url, data=data, stream=True, auth=auth)

    def iter_lines(self) -> Iterator[Any]:
        try:
            for line in self._response.iter_lines():
                # Twitter sometimes returns empty lines.
                if line:
                    yield line
        except AttributeError as e:
            pass

    def close(self) -> None:
        self._response.close()


class Twitter(BaseResponder):
    """Provides live user feeds from twitter.

    Example module config:

        "botnet": {
            "twitter": {
                "consumer_key": "value",
                "consumer_secret": "value",
                "access_token_key": "value",
                "access_token_secret": "value",
                "follow": {
                    "197263266": ["#channel"]
                }
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'twitter'
    deltatime = 10

    def __init__(self, config):
        super(Twitter, self).__init__(config)
        config_reloaded.connect(self.on_config_reloaded)
        self.stop_event = None
        self.api = None

    def start(self):
        super(Twitter, self).start()
        self.start_twitter()

    def stop(self):
        super(Twitter, self).stop()
        self.stop_twitter()

    def start_twitter(self):
        self.stop_event = threading.Event()
        t = threading.Thread(target=self.run)
        t.daemon = True
        t.start()

    def stop_twitter(self):
        self.stop_event.set()
        if self.api:
            self.api.close()

    def on_config_reloaded(self, *args, **kwargs):
        self.stop_twitter()
        self.start_twitter()

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.work()
                self.stop_event.wait(self.deltatime)
            except Exception as e:
                on_exception.send(self, e=e)

    def work(self):
        follow = self.config_get('follow', {})
        if not follow:
            return
        self.api = API(consumer_key=self.config_get('consumer_key'),
                       consumer_secret=self.config_get('consumer_secret'),
                       access_token_key=self.config_get('access_token_key'),
                       access_token_secret=self.config_get('access_token_secret'),
                       follow=list(follow.keys()))
        try:
            for line in self.api.iter_lines():
                try:
                    data = json.loads(line.decode())
                    self.handle_line(data)
                except Exception as e:
                    on_exception.send(self, e=e)
        finally:
            self.api.close()

    def handle_line(self, line):
        if 'warning'in line:
            self.logger.warning(line)
            return

        follow = self.config_get('follow', {})
        if not 'text' in line \
                or not 'user' in line \
                or not line['user']['id_str'] in follow:
            return
        text = '"{text}" - @{username}'.format(
            text=line['text'],
            username=line['user']['screen_name']
        )
        for channel in follow[line['user']['id_str']]:
            msg = Message(command='PRIVMSG', params=[channel, text])
            message_out.send(self, msg=msg)


mod = Twitter
