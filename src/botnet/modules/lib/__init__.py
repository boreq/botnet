"""
    Various utilities which are not a part of the actual module system
    implementation but rather form a library which can be used by modules.
"""

from enum import Enum, unique
from .cache import BaseCache, MemoryCache
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


_COLOR = chr(0x03)


@unique
class Color(Enum):
    GREEN = '03'
    RED = '04'


def colored(text: str, color: Color) -> str:
    # in theory spaces are allowed but if we naively break up long lines later then the colors will break unless we
    # do what we do here
    parts = text.split(' ')
    parts = [_COLOR + color.value + part + _COLOR for part in parts]
    return ' '.join(parts)


__all__ = [
    'BaseCache',
    'MemoryCache',
    'get_url',
    'divide_text',
    'Color',
    'colored',
]
