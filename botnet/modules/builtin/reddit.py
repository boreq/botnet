import random
import re
import threading
from .. import BaseResponder
from ..lib import get_url, parse_command, catch_other


class APIError(Exception):
    pass


class RedditAPI(object):

    url_root = 'https://reddit.com'

    def _get(self, url, **params):
        """Performs an API GET request.

        params: GET request parameters.
        """
        url = self.url_root + url
        try:
            r = get_url(url, params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            raise APIError('API error')

    def get_random_posts(self, subreddit=None):
        """Gets random posts."""
        if subreddit:
            m = re.match('[a-zA-Z0-9]+', subreddit)
            if m is None:
                raise APIError('Invalid subreddit name')
            url = '/r/%s/hot.json' % subreddit
        else:
            url = '/hot.json'
        return self._get(url)


class Reddit(BaseResponder):
    """Implements Reddit related functionality.

    Example module config:

        "botnet": {
            "reddit": {
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'reddit'
    api_class = RedditAPI

    def __init__(self, config):
        super(Reddit, self).__init__(config)
        self.api = self.api_class()

    @catch_other(APIError, 'API error')
    def get_post(self, subreddit, force_external=False):
        p = self.api.get_random_posts(subreddit)
        p = p['data']['children']
        for i in range(5):
            tp = random.choice(p)
            tp = tp['data']
            if not force_external or (force_external and not tp['is_self']):
                return tp['url']
        raise APIError('Could not find a post which is not a self post')

    def in_background(self, f):
        """Launches a function in a separate thread."""
        t = threading.Thread(target=f)
        t.daemon = True
        t.run()

    @parse_command([('subreddit', '*')], launch_invalid=False)
    def command_reddit(self, msg, args):
        """Returns a random link or self post from Reddit.

        Syntax: reddit [SUBREDDIT]
        """
        subreddit = ' '.join(args.subreddit)
        def f():
            try:
                r = self.get_post(subreddit, force_external=False)
                self.respond(msg, r)
            except Exception as e:
                self.respond(msg, str(e))
        self.in_background(f)

    @parse_command([('subreddit', '*')], launch_invalid=False)
    def command_reddit_link(self, msg, args):
        """Returns a random link from Reddit.

        Syntax: reddit_link [SUBREDDIT]
        """
        subreddit = ' '.join(args.subreddit)
        def f():
            try:
                r = self.get_post(subreddit, force_external=True)
                self.respond(msg, r)
            except Exception as e:
                self.respond(msg, str(e))
        self.in_background(f)


mod = Reddit
