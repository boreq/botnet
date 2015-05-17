"""
    Contains cache implementations which can be used by the modules, for example
    to cache results acquired from various online APIs.
"""

import datetime
import hashlib


def get_md5(string):
    """Returns a hash of a string."""
    m = hashlib.md5()
    m.update(string.encode('utf-8'))
    return m.hexdigest()


class BaseCache(object):
    """Base cache class."""

    def __init__(self, default_timeout=300):
        self.default_timeout = default_timeout

    def set(self, key, value, timeout=None):
        """Sets a value of a key. Returns True on sucess or False in case of
        errors.
        """
        return True

    def get(self, key):
        """Returns a value of a key or None if a key does not exist."""
        return None


class MemoryCache(BaseCache):
    """Simple cache. 100% thread unsafety guaranteed.

    default_timeout: timeout used by the set method [seconds].
    """

    def __init__(self, default_timeout=300):
        super(MemoryCache, self).__init__(default_timeout)
        self._data = {}

    def _prepare_key(self, key):
        """Prepares a key before using it."""
        return get_md5(key)

    def _clean(self):
        """Removes expired values."""
        for key in self._data.copy().keys():
            try:
                expires, value = self._data[key]
                if expires < datetime.datetime.now():
                    self._data.pop(key)
            except KeyError:
                pass

    def set(self, key, value, timeout=None):
        self._clean()
        key = self._prepare_key(key)
        if timeout is None:
            timeout = self.default_timeout
        expires = datetime.datetime.now() + datetime.timedelta(seconds=timeout)
        self._data[key] = (expires, value)
        return True

    def get(self, key):
        try:
            key = self._prepare_key(key)
            expires, value = self._data[key]
            if expires > datetime.datetime.now():
                return value
            else:
                return None
        except KeyError:
            return None
