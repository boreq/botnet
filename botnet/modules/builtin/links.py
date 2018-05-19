import threading
from ...helpers import is_channel_name
from ...signals import on_exception
from .. import BaseResponder
from urllib.parse import urlparse 
import requests
from bs4 import BeautifulSoup


class Links(BaseResponder):
    """Reads titles of the links posted by the users.
    
    Example module config:

        "botnet": {
            "links": {
                "include_domain": true,
                "max_links": 5,
                "channels": [
                    "#example"
                ]
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'links'

    character_limit = 80
    timeout = 30 # [seconds]
    max_links = 5

    def __init__(self, config):
        super().__init__(config)

    def get_domain(self, url):
        parsed_uri = urlparse(url)
        return '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)

    def get_title(self, url):
        headers = {
            'Accept-Language': 'en-US,en;q=0.5'
        }
        r = requests.get(url, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        if soup.title:
            title = ' '.join(soup.title.text.splitlines())
            title = title.strip()
            if len(title) > self.character_limit:
                title = title[:self.character_limit] + '...'
            return title
        return None

    def handle_privmsg(self, msg):
        if not is_channel_name(msg.params[0]):
            return

        if not msg.params[0] in self.config_get('channels', []):
            return

        urls = set()
        for element in msg.params[1].split():
            if element.startswith('http://') or element.startswith('https://'):
                urls.add(element)

        if len(urls) <= self.config_get('max_links', self.max_links):
            for url in urls:
                def f():
                    try:
                        title = self.get_title(url)
                        if title:
                            if self.config_get('include_domain', True):
                                text = '%s - %s' % (title, self.get_domain(url))
                            else:
                                text = title
                            self.respond(msg, '[ %s ]' % text)
                    except requests.exceptions.HTTPError as e:
                        pass
                    except Exception as e:
                        on_exception.send(self, e=e)

                t = threading.Thread(target=f, daemon=True)
                t.start()


mod = Links
