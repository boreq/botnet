import json
import threading
from datetime import date, datetime
from .. import BaseResponder
from ..lib import MemoryCache, parse_command, get_url


class APIError(Exception):
    pass


class TheTVDB(object):

    version = '2.1.1'

    def __init__(self, config_get):
        self.config_get = config_get
        # cache which stores series ids (series_name -> series_id)
        self.id_cache = MemoryCache(default_timeout=600)
        # cache which stores the data from the API (series_name -> episodes)
        self.episodes_cache = MemoryCache(default_timeout=600)
        # cache which stores the data from the API (series_name -> series_info)
        self.series_cache = MemoryCache(default_timeout=600)

    def _base_get_url(self, *args, **kwargs):
        if not 'headers' in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Content-Type'] = 'application/json'
        kwargs['headers']['Accept'] = 'application/vnd.thetvdb.v%s' % self.version
        
        if 'data' in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])
        r = get_url(*args, **kwargs)
        j = r.json()
        if 'Error' in j:
            raise APIError(j['Error'])
        return r

    def _get_url(self, *args, **kwargs):
        if not 'headers' in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Authorization'] = 'Bearer %s' % self._get_token()
        return self._base_get_url(*args, **kwargs)

    def _get_token(self):
        if self.config_get('api_key', None) is None:
            raise APIError('API key missing.')
        url = self.config_get('login_api_url')
        data = {'apikey': self.config_get('api_key')}
        r = self._base_get_url(url, method='POST', data=data)
        return r.json()['token']

    def _get_series_id(self, series_name):
        """Gets the ID used in further queries."""
        rw = self.id_cache.get(series_name)
        if not rw:
            try:
                params = {'name': series_name}
                r = self._get_url(self.config_get('search_api_url'), params=params)
                data = r.json()['data']
                rw = data[0]['id']
            except:
                raise APIError('Could not find the TV series with that name.')
            self.id_cache.set(series_name, rw)
        return rw

    def _get_all_series_episodes(self, series_id, page=1):
        """Resursively queries the api to get all episodes from the series."""
        url = self.config_get('episodes_api_url').format(id=series_id)
        r = self._get_url(url, params={'page': page})
        j = r.json()
        rw = j['data']
        if j['links']['next'] is not None:
            rw.extend(self._get_all_series_episodes(series_id, page=j['links']['next']))
        return rw

    def get_series_episodes(self, series_name):
        """Gets all episodes of a TV series."""
        rw = self.episodes_cache.get(series_name)
        if not rw:
            series_id = self._get_series_id(series_name)
            rw = self._get_all_series_episodes(series_id)
            self.episodes_cache.set(series_name, rw)
        return rw

    def get_series_info(self, series_name):
        """Gets basic information about a TV series."""
        rw = self.series_cache.get(series_name)
        if not rw:
            series_id = self._get_series_id(series_name)
            url = self.config_get('series_api_url').format(id=series_id)
            r = self._get_url(url)
            rw = r.json()['data']
            self.series_cache.set(series_name, rw)
        return rw

    def _find_next_episode(self, episodes):
        """Searches for the next episode."""
        today = date.today()
        rw = None
        timespan = None

        # Search for the episode which airs next (air date is the closest to now)
        for episode in episodes:
            try:
                airdate = datetime.strptime(episode['firstAired'], '%Y-%m-%d')
                airdate = airdate.date()
                if airdate >= today:
                    ctimespan = airdate - today
                    if timespan is None or ctimespan < timespan:
                        rw = episode
                        timespan = ctimespan
            except:
                continue
        return rw

    def get_next_episode_text(self, series_name):
        """Gets the text with the information about the next episode."""
        series_episodes = self.get_series_episodes(series_name)
        series_info = self.get_series_info(series_name)

        try:
            series_title = series_info['seriesName']
        except:
            series_title = '<series title unknown>'

        next_episode = self._find_next_episode(series_episodes)
        if next_episode is not None:
            text = '{series_title}: Episode {season}x{episode} "{episode_title}" will air on {date}'.format(
                    series_title=series_title,
                    season=next_episode.get('airedSeason', '<season unknown>'),
                    episode=next_episode.get('airedEpisodeNumber', '<number unknown>'),
                    episode_title=next_episode.get('episodeName', '<name unknown>'),
                    date=next_episode.get('firstAired', '<no date>'))
        else:
            text = '{series_title}: No next episode found'.format(series_title=series_title)

        return text


class TV(BaseResponder):
    """Various TV related features. To use this module you need to acquire the
    API key from https://thetvdb.com/.

    Example module config:

        "botnet": {
            "tv": {
                "api_key": "your_api_key"
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'tv'

    default_config = {
        'login_api_url': 'https://api.thetvdb.com/login',
        'search_api_url': 'https://api.thetvdb.com/search/series',
        'episodes_api_url': 'https://api.thetvdb.com/series/{id}/episodes',
        'series_api_url': 'https://api.thetvdb.com/series/{id}',
    }

    def __init__(self, config):
        super().__init__(config)
        self.api = TheTVDB(self.config_get)

    @parse_command([('series_name', '+')], launch_invalid=False)
    def command_next_episode(self, msg, args):
        """Returns the information about the next episode of a TV series.

        Syntax: next_episode EPISODE_NAME
        """
        series_name = ' '.join(args.series_name)
        def f():
            try:
                text = self.api.get_next_episode_text(series_name)
                self.respond(msg, text)
            except Exception as e:
                self.respond(msg, str(e))
        t = threading.Thread(target=f)
        t.start()


mod = TV
