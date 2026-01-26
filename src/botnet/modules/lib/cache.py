"""
    Contains cache implementations which can be used by the modules, for example
    to cache results acquired from various online APIs.
"""

from typing import TypeVar, Generic
import datetime


K = TypeVar('K')
V = TypeVar('V')


class BaseCache(Generic[K, V]):
    default_timeout_in_seconds: float

    def __init__(self, default_timeout_in_seconds: float = 60 * 5):
        self.default_timeout_in_seconds = default_timeout_in_seconds

    def set(self, key: K, value: V, timeout_in_seconds: float | None = None) -> None:
        """Sets a value of a key."""
        raise NotImplementedError

    def get(self, key: K) -> V | None:
        """Returns a value of a key or None if a key does not exist."""
        raise NotImplementedError

    def delete(self, key: K) -> None:
        """Deletes a key from the cache returning true if the key existed or false if the key didn't exist."""
        raise NotImplementedError


class MemoryCache(BaseCache[K, V]):
    """Simple cache. 100% thread unsafety guaranteed.

    default_timeout: timeout used by the set method [seconds].
    """

    def __init__(self, default_timeout_in_seconds: float = 60 * 5) -> None:
        super().__init__(default_timeout_in_seconds)
        self._data: dict[K, tuple[datetime.datetime, V]] = {}

    def set(self, key: K, value: V, timeout_in_seconds: float | None = None) -> None:
        self._remove_expired_values()
        if timeout_in_seconds is None:
            timeout_in_seconds = self.default_timeout_in_seconds
        expires = datetime.datetime.now() + datetime.timedelta(seconds=timeout_in_seconds)
        self._data[key] = (expires, value)

    def get(self, key: K) -> V | None:
        try:
            expires, value = self._data[key]
            if expires > datetime.datetime.now():
                return value
            else:
                return None
        except KeyError:
            return None

    def delete(self, key: K) -> None:
        try:
            self._data.pop(key)
        except KeyError:
            pass

    def _remove_expired_values(self) -> None:
        for key in self._data.copy().keys():
            try:
                expires, value = self._data[key]
                if expires < datetime.datetime.now():
                    self._data.pop(key)
            except KeyError:
                pass
