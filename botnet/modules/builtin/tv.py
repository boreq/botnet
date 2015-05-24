import threading
import xmltodict
from datetime import datetime
from .. import BaseResponder, parse_command
from ..network import get_url
from ..cache import MemoryCache


class APIError(Exception):
    pass


class TheTVDB(object):

    def __init__(self, config_get):
        self.config_get = config_get
        # cache which stores series ids (series_name -> series_id)
        self.id_cache = MemoryCache(default_timeout=600)
        # cache which stores the data from the API (series_name -> series_data)
        self.info_cache = MemoryCache(default_timeout=600)

    def _get_series_id(self, series_name):
        """Gets the ID used in further queries."""
        rw = self.id_cache.get(series_name)
        if not rw:
            # get the data
            try:
                params = {'seriesname': series_name}
                r = get_url(self.config_get('search_api_url'), params=params)
                r.raise_for_status()
            except:
                raise TVError('Could not connect to the API.')

            # parse the data
            try:
                data = xmltodict.parse(r.content)
            except:
                raise TVError('Could not parse the API response.')

            # find the data for the first episode
            try:
                rw = data['Data']['Series'][0]['id']
            except:
                raise APIError('Could not find the TV series with that name.')

            self.id_cache.set(series_name, rw)
        return rw

    def get_series_info(self, series_name):
        """Gets all available information about a TV series."""
        if self.config_get('api_key', None) is None:
            raise TVError('API key missing.')

        series_id = self._get_series_id(series_name)
        rw = self.info_cache.get(series_name)
        if not rw:
            # get the data
            try:
                url = self.config_get('series_api_url')
                url = url.format(api_key=self.config_get('api_key'), id=series_id)
                r = get_url(url)
                r.raise_for_status()
            except:
                raise TVError('Could not connect to the API.')

            # parse the data
            try:
                rw = xmltodict.parse(r.content)
            except:
                raise APIError('Could not parse the API response.')
            self.info_cache.set(series_name, rw)
        return rw

    def find_next_episode(self, series_info):
        """Returns the data about the next episode."""
        now = datetime.now()
        rw = None
        timespan = None

        # Search for the episode which airs next (air date is the closest to now)
        for episode in series_info['Data']['Episode']:
            try:
                date_string = episode['FirstAired']
                airdate = datetime.strptime(date_string, '%Y-%m-%d')
                if airdate > now:
                    ctimespan = airdate - now
                    if timespan is None or ctimespan < timespan:
                        rw = episode
                        timespan = ctimespan
            except:
                continue
        return rw

    def get_next_episode_text(self, series_name):
        """Gets the text with the information about the next episode."""
        series_info = self.get_series_info(series_name)
        episode = self.find_next_episode(series_info)

        # series title
        try:
            series_title = series_info['Data']['Series']['SeriesName']
        except:
            series_title = '<series title unknown>'

        # main text
        if episode:
            text = '{series_title}: Episode {season}x{episode} "{episode_title}" will air {date}'.format(
                    series_title=series_title,
                    season=episode.get('SeasonNumber', '<season unknown>'),
                    episode=episode.get('EpisodeNumber', '<number unknown>'),
                    episode_title=episode.get('EpisodeName', '<name unknown>'),
                    date=episode.get('FirstAired', '<no date>'))
        else:
            text = '{series_title}: No next episode found'.format(series_title=series_title)

        return text


class TV(BaseResponder):
    """Various TV related features. To use this module you need to acquire the
    API key from http://thetvdb.com/.

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
        'search_api_url': 'https://thetvdb.com/api/GetSeries.php',
        'series_api_url': 'http://thetvdb.com/api/{api_key}/series/{id}/all/en.xml'
    }

    def __init__(self, config):
        super(TV, self).__init__(config)
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
