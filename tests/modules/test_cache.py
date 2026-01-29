import time

import pytest

from botnet.modules.lib import cache

type TestedMemoryCache = cache.MemoryCache[str, str]


class TestMemoryCache(object):

    def make_cache(self) -> TestedMemoryCache:
        return cache.MemoryCache(0.1)

    @pytest.fixture
    def c(self) -> TestedMemoryCache:
        return self.make_cache()

    def test_base_get(self, c: TestedMemoryCache) -> None:
        assert c.get('key') is None

    def test_base_set_get(self, c: TestedMemoryCache) -> None:
        c.set('key', 'value')
        assert c.get('key') == 'value'

    def test_multi_set(self, c: TestedMemoryCache) -> None:
        c.set('key1', 'value1')
        c.set('key2', 'value2')
        assert c.get('key1') == 'value1'
        assert c.get('key2') == 'value2'

    def test_base_default_timeout(self, c: TestedMemoryCache) -> None:
        c.set('key', 'value')
        time.sleep(0.1)
        assert c.get('key') is None

    def test_base_custom_timeout(self, c: TestedMemoryCache) -> None:
        c.set('key', 'value', 0.2)
        time.sleep(0.1)
        assert c.get('key') == 'value'
        time.sleep(0.11)
        assert c.get('key') is None

    def test_cleanup(self, c: TestedMemoryCache) -> None:
        assert len(c._data) == 0
        c.set('key', 'value')
        c.set('key2', 'value')
        assert len(c._data) == 2
        time.sleep(0.1)
        c.set('key3', 'value')
        assert len(c._data) == 1
