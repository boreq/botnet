import threading
import twitter
from .. import BaseResponder
from ...signals import on_exception, message_out, config_reloaded
from ...message import Message


class API(twitter.Api):

    def custom_stream_filter(self, follow=None, track=None, locations=None,
                             languages=None, delimited=None,
                             stall_warnings=None):
        """https://github.com/bear/python-twitter/blob/master/twitter/api.py"""
        if all((follow is None, track is None, locations is None)):
            raise ValueError({'message': "No filter parameters specified."})
        url = '%s/statuses/filter.json' % self.stream_url
        data = {}
        if follow is not None:
            data['follow'] = ','.join(follow)
        if track is not None:
            data['track'] = ','.join(track)
        if locations is not None:
            data['locations'] = ','.join(locations)
        if delimited is not None:
            data['delimited'] = str(delimited)
        if stall_warnings is not None:
            data['stall_warnings'] = str(stall_warnings)
        if languages is not None:
            data['language'] = ','.join(languages)
        return self._RequestStream(url, 'POST', data=data)

    def yield_lines(self, resp):
        for line in resp.iter_lines():
            if line:
                data = self._ParseAndCheckTwitter(line.decode('utf-8'))
                yield data


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
        self.resp = None

    def start(self):
        super(Twitter, self).start()
        self.api = API(consumer_key=self.config_get('consumer_key'),
                       consumer_secret=self.config_get('consumer_secret'),
                       access_token_key=self.config_get('access_token_key'),
                       access_token_secret=self.config_get('access_token_secret'))
        self.start_twitter()

    def stop(self):
        super(Twitter, self).stop()
        self.stop_twitter()

    def start_twitter(self):
        self.stop_event = threading.Event()
        self.done_event = threading.Event()
        self.resp = None
        t = threading.Thread(target=self.run)
        t.daemon = True
        t.start()

    def stop_twitter(self):
        if self.stop_event is not None:
            self.stop_event.set()
        if self.resp is not None:
            self.resp.close()
        if self.done_event is not None:
            self.done_event.wait()

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
        try:
            follow = self.config_get('follow', {})
            if follow:
                try:
                    self.resp = self.api.custom_stream_filter(follow=list(follow.keys()))
                    for line in self.api.yield_lines(self.resp):
                        try:
                            self.handle_line(line)
                        except Exception as e:
                            on_exception.send(self, e=e)
                finally:
                    self.resp.close()
        finally:
            self.done_event.set()

    def handle_line(self, line):
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
