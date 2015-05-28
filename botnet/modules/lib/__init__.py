"""
    Various utilities which are not a part of the actual module system
    implementation but rather form a library which can be used by modules.
"""
from .cache import BaseCache, MemoryCache
from .decorators import parse_command, catch_other
from .network import get_url
