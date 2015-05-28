from functools import wraps
import threading
from .. import BaseResponder
from ..lib import MemoryCache, get_url, parse_command
from ...signals import on_exception


class APIError(Exception):
    pass


def api_func(f):
    """Decorator which catches exceptions which don't inherit from APIError 
    and throws an APIError instead.
    """
    @wraps(f)
    def df(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIError:
            raise
        except Exception:
            raise APIError('API error')
    return df


class GithubAPI(object):

    url_root = 'https://api.github.com'

    def __init__(self):
        self._repo_cache = MemoryCache(default_timeout=600)
        self._user_cache = MemoryCache(default_timeout=600)

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

    def search_repositories(self, q):
        rw = self._repo_cache.get(q)
        if rw is None:
            rw = self._get('/search/repositories', q=q)
            self._repo_cache.set(q, rw)
        return  rw

    def search_users(self, q):
        rw = self._user_cache.get(q)
        if rw is None:
            rw = self._get('/search/users', q=q)
            self._user_cache.set(q, rw)
        return  rw


class Github(BaseResponder):
    """Implements Github search."""

    ignore_help = False
    ibip_repo = 'https://github.com/boreq/botnet'

    def __init__(self, config):
        super(Github, self).__init__(config)
        self.api = GithubAPI()

    @api_func
    def get_repo(self, phrase):
        r = self.api.search_repositories(phrase)
        return self.get_first(r)

    @api_func
    def get_user(self, phrase):
        r = self.api.search_users(phrase)
        return self.get_first(r)

    def get_first(self, r):
        d = r['items']
        if not d:
            raise APIError('No results')
        return d[0]['html_url']

    def in_background(self, f):
        """Launches a function in a separate thread."""
        t = threading.Thread(target=f)
        t.daemon = True
        t.run()

    @parse_command([('phrase', '+')], launch_invalid=False)
    def command_github(self, msg, args):
        """Search Github repositories.

        Syntax: github PHRASE
        """
        phrase = ' '.join(args.phrase)
        def f():
            try:
                r = self.get_repo(phrase)
                self.respond(msg, r)
            except Exception as e:
                self.respond(msg, str(e))
        self.in_background(f)

    @parse_command([('phrase', '+')], launch_invalid=False)
    def command_github_user(self, msg, args):
        """Search Github users.

        Syntax: github_user PHRASE
        """
        phrase = ' '.join(args.phrase)
        def f():
            try:
                r = self.get_user(phrase)
                self.respond(msg, r)
            except Exception as e:
                self.respond(msg, str(e))
        self.in_background(f)


mod = Github
