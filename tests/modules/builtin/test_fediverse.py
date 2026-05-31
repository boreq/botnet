from typing import Any
from typing import Optional

import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.modules.builtin.fediverse import Fediverse
from botnet.modules.builtin.fediverse import RateLimiter
from botnet.modules.builtin.fediverse import URLCache
from botnet.modules.builtin.fediverse import extract_canonical_url
from botnet.modules.builtin.fediverse import extract_urls

from ...conftest import MakePrivmsgFixture
from ...conftest import ModuleHarness
from ...conftest import ModuleHarnessFactory


class TestExtractUrls:
    def test_extract_single_url(self) -> None:
        text = "Check this out: https://example.com/@user/123456"
        urls = extract_urls(text)
        assert urls == ["https://example.com/@user/123456"]

    def test_extract_cross_instance_url(self) -> None:
        text = "https://chaos.social/@robpike@hachyderm.io/116660384710304342"
        urls = extract_urls(text)
        assert urls == ["https://chaos.social/@robpike@hachyderm.io/116660384710304342"]

    def test_extract_users_statuses_url(self) -> None:
        text = "https://example.com/users/alice/statuses/12345"
        urls = extract_urls(text)
        assert urls == ["https://example.com/users/alice/statuses/12345"]

    def test_extract_notes_url(self) -> None:
        text = "https://example.com/notes/abc123xyz"
        urls = extract_urls(text)
        assert urls == ["https://example.com/notes/abc123xyz"]

    def test_extract_objects_url(self) -> None:
        text = "https://example.com/objects/uuid-123"
        urls = extract_urls(text)
        assert urls == ["https://example.com/objects/uuid-123"]

    def test_extract_multiple_urls(self) -> None:
        text = (
            "First: https://example.com/@user/123 and second: "
            "https://other.com/@admin/456"
        )
        urls = extract_urls(text)
        assert set(urls) == {
            "https://example.com/@user/123",
            "https://other.com/@admin/456",
        }

    def test_strip_trailing_punctuation(self) -> None:
        text = "Check https://example.com/@user/123."
        urls = extract_urls(text)
        assert urls == ["https://example.com/@user/123"]

    def test_strip_multiple_trailing_chars(self) -> None:
        text = "Look: https://example.com/@user/123!?."
        urls = extract_urls(text)
        assert urls == ["https://example.com/@user/123"]

    def test_no_urls(self) -> None:
        text = "This is just plain text without any URLs"
        urls = extract_urls(text)
        assert urls == []

    def test_non_fediverse_urls_ignored(self) -> None:
        text = "Check https://google.com and https://example.com/@user/123"
        urls = extract_urls(text)
        assert urls == ["https://example.com/@user/123"]

    def test_deduplication(self) -> None:
        text = (
            "https://example.com/@user/123 and "
            "https://example.com/@user/123 again"
        )
        urls = extract_urls(text)
        assert urls == ["https://example.com/@user/123"]


class TestExtractCanonicalUrl:
    def test_string_url(self) -> None:
        obj = {"url": "https://example.com/@user/123"}
        result = extract_canonical_url(obj)
        assert result == "https://example.com/@user/123"

    def test_array_of_strings(self) -> None:
        obj = {"url": ["https://example.com/@user/123", "https://other.com"]}
        result = extract_canonical_url(obj)
        assert result == "https://example.com/@user/123"

    def test_array_of_link_objects(self) -> None:
        obj = {
            "url": [
                {"type": "Link", "href": "https://example.com/@user/123"},
                {"type": "Link", "href": "https://other.com"},
            ]
        }
        result = extract_canonical_url(obj)
        assert result == "https://example.com/@user/123"

    def test_mixed_array(self) -> None:
        obj = {
            "url": [
                "https://example.com/@user/123",
                {"type": "Link", "href": "https://other.com"},
            ]
        }
        result = extract_canonical_url(obj)
        assert result == "https://example.com/@user/123"

    def test_no_url_field(self) -> None:
        obj = {"type": "Note", "content": "Hello"}
        result = extract_canonical_url(obj)
        assert result is None

    def test_empty_url_field(self) -> None:
        obj = {"url": ""}
        result = extract_canonical_url(obj)
        assert result is None

    def test_link_object_without_href(self) -> None:
        obj = {"url": [{"type": "Link"}]}
        result = extract_canonical_url(obj)
        assert result is None


class FakeResolver:
    """Records resolve() calls and returns canned answers."""

    def __init__(self) -> None:
        self.results: dict[str, Optional[str]] = {}
        self.calls: list[str] = []

    def resolve(self, url: str, timeout: int) -> Optional[str]:
        self.calls.append(url)
        return self.results.get(url)


class FediverseForTest(Fediverse):
    def __init__(self, config: Config) -> None:
        self.mock_resolver = FakeResolver()
        super().__init__(config)

    def _resolve(self, url: str, timeout: int) -> Optional[str]:
        return self.mock_resolver.resolve(url, timeout)


def test_resolves_url_in_configured_channel(
    make_privmsg: MakePrivmsgFixture,
    tested_fediverse: ModuleHarness[FediverseForTest],
) -> None:
    resolver = tested_fediverse.module.mock_resolver
    url = "https://chaos.social/@robpike@hachyderm.io/116660384710304342"
    resolver.results[url] = "https://hachyderm.io/@robpike/116660384710304342"

    msg = make_privmsg(f"look: {url}", nick="author", target="#channel")
    tested_fediverse.receive_message_in(msg)

    tested_fediverse.expect_message_out_signals([
        {
            "msg": Message.new_from_string(
                "PRIVMSG #channel :author meant to say: "
                "https://hachyderm.io/@robpike/116660384710304342"
            )
        }
    ])


def test_ignores_message_in_unconfigured_channel(
    make_privmsg: MakePrivmsgFixture,
    tested_fediverse: ModuleHarness[FediverseForTest],
) -> None:
    resolver = tested_fediverse.module.mock_resolver
    url = "https://example.com/@user/123"
    resolver.results[url] = "https://other.com/@user/123"

    msg = make_privmsg(f"look: {url}", nick="author", target="#other")
    tested_fediverse.receive_message_in(msg)

    tested_fediverse.expect_message_out_signals([])
    assert resolver.calls == []


def test_no_reply_when_not_cross_host(
    make_privmsg: MakePrivmsgFixture,
    tested_fediverse: ModuleHarness[FediverseForTest],
) -> None:
    resolver = tested_fediverse.module.mock_resolver
    url = "https://example.com/@user/123"
    resolver.results[url] = None  # resolver found nothing canonical

    msg = make_privmsg(f"look: {url}", nick="author", target="#channel")
    tested_fediverse.receive_message_in(msg)

    def assert_called(trapped: list[dict[str, Any]]) -> None:
        assert resolver.calls == [url]
        assert trapped == []

    tested_fediverse.message_out_trap.wait(assert_called)


def test_resolves_multiple_urls(
    make_privmsg: MakePrivmsgFixture,
    tested_fediverse: ModuleHarness[FediverseForTest],
) -> None:
    resolver = tested_fediverse.module.mock_resolver
    a = "https://example.com/@user/1"
    b = "https://other.com/@admin/2"
    resolver.results[a] = "https://home.example/@user/1"
    resolver.results[b] = "https://home.other/@admin/2"

    msg = make_privmsg(f"two links {a} and {b}", nick="author", target="#channel")
    tested_fediverse.receive_message_in(msg)

    def two_replies(trapped: list[dict[str, Any]]) -> None:
        bodies = {kwargs["msg"].params[1] for kwargs in trapped}
        assert bodies == {
            "author meant to say: https://home.example/@user/1",
            "author meant to say: https://home.other/@admin/2",
        }

    tested_fediverse.message_out_trap.wait(two_replies)


@pytest.fixture()
def tested_fediverse(
    module_harness_factory: ModuleHarnessFactory,
) -> ModuleHarness[FediverseForTest]:
    config = Config(
        {
            "module_config": {
                "botnet": {
                    "fediverse": {
                        "channels": ["#channel"],
                        "cache_ttl": 300,
                        "http_timeout": 10,
                        "rate_limit": 5,
                    }
                }
            }
        }
    )

    return module_harness_factory.make(FediverseForTest, config)


class TestURLCache:
    def test_caches_non_none_result(self) -> None:
        cache = URLCache(ttl=300)
        calls = []

        def fetch() -> Optional[str]:
            calls.append(1)
            return "value"

        assert cache.fetch("k", fetch) == "value"
        assert cache.fetch("k", fetch) == "value"
        assert len(calls) == 1  # second hit served from cache

    def test_does_not_cache_none(self) -> None:
        cache = URLCache(ttl=300)
        calls = []

        def fetch() -> Optional[str]:
            calls.append(1)
            return None

        assert cache.fetch("k", fetch) is None
        assert cache.fetch("k", fetch) is None
        assert len(calls) == 2  # None never cached, so recomputed

    def test_expired_entry_recomputed(self) -> None:
        cache = URLCache(ttl=0)  # entries expire immediately
        calls = []

        def fetch() -> Optional[str]:
            calls.append(1)
            return "value"

        assert cache.fetch("k", fetch) == "value"
        assert cache.fetch("k", fetch) == "value"
        assert len(calls) == 2


class TestRateLimiter:
    def test_allows_up_to_max(self) -> None:
        limiter = RateLimiter(max_per_minute=3)
        assert [limiter.allow("#chan") for _ in range(4)] == [
            True,
            True,
            True,
            False,
        ]

    def test_limits_are_per_channel(self) -> None:
        limiter = RateLimiter(max_per_minute=1)
        assert limiter.allow("#a") is True
        assert limiter.allow("#b") is True
        assert limiter.allow("#a") is False
