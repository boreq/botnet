"""
    Various utilities which are not a part of the actual module system
    implementation but rather form a library which can be used by modules.
"""

# flake8: noqa: F401

from .cache import BaseCache, MemoryCache
from .decorators import catch_other
from .network import get_url

def divide_text(text: str, max_len: int) -> list[str]:
    lines: list[str] = []

    for part in text.split(' '):
        if len(lines) == 0:
            lines.append(part)
        else:
            if len(part) + len(lines[-1]) + 1 <= max_len:
                lines[-1] += ' ' + part
            else:
                lines.append(part)

    return lines