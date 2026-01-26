import threading
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from ...config import Config
from ...message import Channel
from ...message import IncomingPrivateMessage
from ...signals import on_exception
from .. import BaseResponder


@dataclass()
class LinksConfig:
    channels: list[str]
    domains: list[str]

    def __post_init__(self) -> None:
        for domain in self.domains:
            if domain == '':
                raise ValueError('domains cannot contain an empty string')
            if '/' in domain:
                raise ValueError('domains cannot contain slashes')


class Links(BaseResponder[LinksConfig]):
    """Reads titles of the links posted by the users.

    Example module config:

        "botnet": {
            "links": {
                "channels": [
                    "#example"
                ],
                "domains": [
                    "example.com",
                    "another.example.com"
                ]
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'links'
    config_class = LinksConfig

    character_limit = 80
    timeout_in_seconds = 5
    max_links = 2

    def __init__(self, config: Config) -> None:
        super().__init__(config)

    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        config = self.get_config()

        channel = msg.target.channel
        if channel is None or channel not in [Channel(s) for s in config.channels]:
            return

        urls = set()
        for element in msg.text.s.split():
            if element.startswith('https://'):
                urls.add(element)

        if len(urls) > self.max_links:
            return

        for url in urls:
            self._maybe_respond_with_title(config, msg, url)

    def _maybe_respond_with_title(self, config: LinksConfig, msg: IncomingPrivateMessage, url: str) -> None:
        parsed_uri = urlparse(url)
        if parsed_uri.scheme != 'https':
            return
        if parsed_uri.netloc not in config.domains:
            return

        def get_and_display_title() -> None:
            try:
                title = self._get_title(url)
                if title:
                    self.respond(msg, f'[ {title} ]')
            except requests.exceptions.HTTPError:
                pass
            except Exception as e:
                on_exception.send(self, e=e)

        t = threading.Thread(target=get_and_display_title, daemon=True)
        t.start()

    def _get_title(self, url: str) -> str | None:
        headers = {
            'Accept-Language': 'en-US,en;q=0.5'
        }
        r = requests.get(url, headers=headers, timeout=self.timeout_in_seconds)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        if soup.title:
            title = ' '.join(soup.title.text.splitlines())
            title = title.strip()
            if len(title) > self.character_limit:
                title = title[:self.character_limit] + '...'
            return title
        return None


mod = Links
