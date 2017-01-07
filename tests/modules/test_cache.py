import pytest
import time
from botnet.modules.lib import cache


class BaseCacheTests(object):

    def make_cache(self):
        """Expected default timeout is 1 second."""
        raise NotImplemented

    @pytest.fixture
    def c(self):
        return self.make_cache()

    def test_base_get(self, c):
        assert c.get('key') is None

    def test_base_set_get(self, c):
        assert c.set('key', 'value')
        assert c.get('key') == 'value'

    def test_multi_set(self, c):
        assert c.set('key1', 'value1')
        assert c.set('key2', 'value2')
        assert c.get('key1') == 'value1'
        assert c.get('key2') == 'value2'

    def test_base_default_timeout(self, c):
        assert c.set('key', 'value')
        time.sleep(1)
        assert c.get('key') is None

    def test_base_custom_timeout(self, c):
        assert c.set('key', 'value', 2)
        time.sleep(1)
        assert c.get('key') == 'value'
        time.sleep(1)
        assert c.get('key') is None


class TestMemoryCache(BaseCacheTests):

    def make_cache(self):
        return cache.MemoryCache(1)

    def test_cleanup(self, c):
        assert len(c._data) == 0
        assert c.set('key', 'value')
        assert c.set('key2', 'value')
        assert len(c._data) == 2
        time.sleep(1)
        assert c.set('key3', 'value')
        assert len(c._data) == 1
