import json
import re
import threading
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import ssl

from botnet.modules import privmsg_message_handler

from ...config import Config
from ...message import Channel
from ...message import IncomingPrivateMessage
from ...signals import on_exception
from .. import BaseResponder


# Matches common ActivityPub status URL shapes:
#   https://instance/@user/1234567890
#   https://instance/@user@other.tld/1234567890    ← cross-instance
#   https://instance/users/user/statuses/1234
#   https://instance/notes/abc123                   (Misskey family)
#   https://instance/objects/uuid                   (Pleroma/Akkoma)
FEDIVERSE_URL_RE = re.compile(
    r"\bhttps?://"
    r"[A-Za-z0-9](?:[A-Za-z0-9._~-]*[A-Za-z0-9])?"  # hostname
    r"(?::\d+)?"  # optional port
    r"(?:"
    r"/@[A-Za-z0-9._%-]+(?:@[A-Za-z0-9._-]+)?/[0-9A-Za-z_-]+ |"
    r"/users/[A-Za-z0-9._%-]+/statuses/[0-9A-Za-z_-]+ |"
    r"/notes/[0-9A-Za-z_-]+ |"
    r"/objects/[0-9A-Za-z_-]+"
    r")"
    r"\b",
    re.VERBOSE,
)


def extract_urls(text: str) -> list[str]:
    """Extract all candidate fediverse URLs from a line of text."""
    urls = FEDIVERSE_URL_RE.findall(text)
    # Strip trailing punctuation
    urls = [u.rstrip(">)].,:!?") for u in urls]
    return list(set(urls))  # deduplicate


def extract_canonical_url(obj: dict[str, Any]) -> Optional[str]:
    """Pull the canonical URL string out of an ActivityPub JSON object.

    The "url" field can be a plain String, an Array of Strings, or an
    Array of Link objects like { "type": "Link", "href": "..." }.
    """
    value = obj.get("url")
    if isinstance(value, str):
        return value if value else None
    if isinstance(value, list):
        for v in value:
            if isinstance(v, str) and v:
                return v
            if isinstance(v, dict):
                if v.get("type") == "Link":
                    href = v.get("href")
                    if isinstance(href, str) and href:
                        return href
    return None


def fetch_activitypub(
    uri: str,
    origin_host: str,
    timeout: int = 10,
    redirect_limit: int = 5,
) -> Optional[str | dict[str, Any]]:
    """Perform an HTTP GET requesting ActivityPub JSON-LD.

    Returns:
        - a String when a 3xx redirect crosses to a different host (that URL
          is already the canonical answer; no further fetch needed)
        - a dict when a 200 response contains parseable AP JSON
        - None on failure or same-host redirect loops
    """
    if redirect_limit == 0:
        return None

    try:
        # Create SSL context that verifies certificates
        ssl_context = ssl.create_default_context()

        req = Request(uri)
        req.add_header(
            "Accept",
            'application/activity+json, '
            'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
        )
        req.add_header("User-Agent", "FediverseBot/1.0 (IRC link resolver)")

        with urlopen(req, timeout=timeout, context=ssl_context) as response:
            status_code = response.status
            content_type = response.headers.get("Content-Type", "")

            if status_code == 200:
                if not any(
                    ct in content_type
                    for ct in ["activity+json", "ld+json", "/json"]
                ):
                    return None
                body = response.read().decode("utf-8")
                obj: dict[str, Any] = json.loads(body)
                return obj

            if status_code in (301, 302, 303, 307, 308):
                location_header = response.headers.get("Location", "")
                if not location_header:
                    return None

                location: str = location_header
                if not location.startswith("http"):
                    # Relative redirect
                    from urllib.parse import urljoin

                    location = urljoin(uri, location)

                new_parsed = urlparse(location)
                new_host = new_parsed.netloc

                # Cross-host redirect: the Location IS the canonical URL
                if new_host.lower() != origin_host.lower():
                    return location

                # Same-host redirect: follow it to get the AP JSON
                return fetch_activitypub(
                    location,
                    origin_host=origin_host,
                    timeout=timeout,
                    redirect_limit=redirect_limit - 1,
                )

            return None

    except (URLError, HTTPError, json.JSONDecodeError, Exception):
        return None


def resolve(raw_url: str, timeout: int = 10) -> Optional[str]:
    """Fetch the ActivityPub representation and return the canonical URL.

    Returns the canonical URL if it lives on a different host, else None.
    """
    origin = urlparse(raw_url)
    if origin.scheme not in ("http", "https"):
        return None

    result = fetch_activitypub(raw_url, origin_host=origin.hostname or "", timeout=timeout)
    if result is None:
        return None

    if isinstance(result, str):
        # Path A: a cross-host redirect gave us the URL directly
        return result

    if isinstance(result, dict):
        # Path B: parse the "url" field out of the AP JSON object
        canonical = extract_canonical_url(result)
        if not isinstance(canonical, str) or not canonical:
            return None
        canonical_parsed = urlparse(canonical)
        canonical_host = canonical_parsed.hostname
        if canonical_host and \
           canonical_host.lower() != (origin.hostname or "").lower():
            return canonical

    return None


@dataclass()
class FediverseConfig:
    channels: list[str]
    cache_ttl: int = 300
    http_timeout: int = 10
    rate_limit: int = 5  # max resolved links per channel per minute


class URLCache:
    """Simple TTL URL cache."""

    def __init__(self, ttl: int = 300) -> None:
        self._ttl = ttl
        self._store: dict[str, Optional[str]] = {}
        self._timestamps: dict[str, float] = {}

    def fetch(self, key: str, fetch_fn) -> Optional[str]:  # type: ignore[no-untyped-def]
        """Get from cache or compute and cache the result."""
        import time

        if key in self._store:
            if time.time() < self._timestamps[key]:
                return self._store[key]
            del self._store[key]
            del self._timestamps[key]

        result: Optional[str] = fetch_fn()

        if result is not None:
            self._store[key] = result
            self._timestamps[key] = time.time() + self._ttl

        return result


class RateLimiter:
    """Per-channel sliding-window rate limiter."""

    def __init__(self, max_per_minute: int = 5) -> None:
        self._max = max_per_minute
        self._counts: dict[str, int] = {}
        self._window: dict[str, float] = {}

    def allow(self, channel: str) -> bool:
        """Check if we can send another message for this channel."""
        import time

        now = time.time()
        if channel not in self._window or now - self._window[channel] >= 60:
            self._counts[channel] = 0
            self._window[channel] = now

        if self._counts[channel] < self._max:
            self._counts[channel] += 1
            return True
        return False


class Fediverse(BaseResponder[FediverseConfig]):
    """Resolves cross-instance Fediverse links to their canonical URLs.

    When a channel message contains a URL like:
      https://chaos.social/@robpike@hachyderm.io/116660384710304342
    the bot fetches the ActivityPub object from the host instance, extracts
    the canonical `url` field (which lives on the original instance), and
    replies with the direct link.

    Example module config:

        "botnet": {
            "fediverse": {
                "channels": ["#channel1", "#channel2"],
                "cache_ttl": 300,
                "http_timeout": 10,
                "rate_limit": 5
            }
        }

    """

    config_namespace = "botnet"
    config_name = "fediverse"
    config_class = FediverseConfig

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        cfg = self.get_config()
        self._cache = URLCache(ttl=cfg.cache_ttl)
        self._limiter = RateLimiter(max_per_minute=cfg.rate_limit)

    @privmsg_message_handler()
    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        config = self.get_config()

        channel = msg.target.channel
        if channel is None or channel not in [Channel(s) for s in config.channels]:
            return

        urls = extract_urls(msg.text.s)
        for url in urls:
            self._maybe_resolve_and_reply(config, msg, url)

    def _maybe_resolve_and_reply(
        self, config: FediverseConfig, msg: IncomingPrivateMessage, url: str
    ) -> None:
        """Resolve a URL in a background thread and reply if canonical."""

        def resolve_and_reply() -> None:
            try:
                canonical = self._cache.fetch(
                    url, lambda: resolve(url, timeout=config.http_timeout)
                )
                if not canonical:
                    return

                channel = msg.target.channel
                if channel is None:
                    return

                if not self._limiter.allow(channel.s):
                    return

                nick = msg.sender.s
                self.respond(msg, f"{nick} meant to say: {canonical}")
            except Exception as e:
                on_exception.send(self, e=e)

        t = threading.Thread(target=resolve_and_reply, daemon=True)
        t.start()


mod = Fediverse
