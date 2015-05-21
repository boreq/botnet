import threading
from datetime import datetime
from xml.etree import ElementTree
from .. import BaseResponder, parse_command
from ..network import get_url
from ..cache import MemoryCache


class TVError(Exception):
    pass


class TV(BaseResponder):
    """Various TV related features.

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
        'search_api_url': 'https://thetvdb.com/api/GetSeries.php?seriesname=silicon',
        'series_api_url': 'http://thetvdb.com/api/{api_key}/series/{id}/all/en.xml'
    }

    def __init__(self, config):
        super(TV, self).__init__(config)
        self.id_cache = MemoryCache(default_timeout=600)
        self.info_cache = MemoryCache(default_timeout=600)

    def get_series_id(self, series_name):
        rw = self.id_cache.get(series_name)
        if not rw:
            params = {'seriesname': series_name}
            r = get_url(self.config_get('search_api_url'), params=params)
            tree = ElementTree.fromstring(r.content)
            rw = tree[0].find('id').text
            self.id_cache.set(series_name, rw)
        return rw

    def get_series_info(self, series_name):
        series_id = self.get_series_id(series_name)
        rw = self.info_cache.get(series_name)
        if not rw:
            url = self.config_get('series_api_url').format(api_key=self.config_get('api_key'),
                                                           id=series_id)
            r = get_url(url)
            rw = r.content
            self.info_cache.set(series_name, rw)
        return rw

    def find_next_episode(self, series_info):
        now = datetime.now()
        episode = None
        timespan = None

        tree = ElementTree.fromstring(series_info)
        for node in tree:
            if node.tag != 'Episode':
                continue
            try:
                date_string = node.find('FirstAired').text
                airdate = datetime.strptime(date_string, '%Y-%m-%d')
                if airdate < now:
                    continue
                ctimespan = airdate - now
                if timespan is None or ctimespan < timespan:
                    episode = node
                    timespan = ctimespan
            except:
                continue
        return episode

    def get_next_episode_text(self, series_name):
        def getinfo(episode, name, default):
            try:
                return episode.find(name).text
            except:
                return default

        series_info = self.get_series_info(series_name)
        episode = self.find_next_episode(series_info)

        if episode:
            text = 'Episode {season}x{episode} "{title}" will air {date}'.format(
                    season=getinfo(episode, 'SeasonNumber', '<season unknown>'),
                    episode=getinfo(episode, 'EpisodeNumber', '<number unknown>'),
                    title=getinfo(episode, 'EpisodeName', '<name unknown>'),
                    date=getinfo(episode, 'FirstAired', '<no date>'))
        else:
            text = 'No next episode found'

        return text

    @parse_command([('series_name', '+')], launch_invalid=False)
    def command_next_episode(self, msg, args):
        if self.config_get('api_key', None) is None:
            self.respond(msg, 'API key missing.')
            return

        series_name = ' '.join(args.series_name)
        def f():
            try:
                text = self.get_next_episode_text(series_name)
                self.respond(msg, text)
            except:
                self.respond(msg, 'API Error')
        t = threading.Thread(target=f)
        t.start()


mod = TV
