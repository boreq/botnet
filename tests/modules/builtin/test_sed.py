import pytest
from botnet.modules.builtin.sed import parse_message


def test_parse_message():
    assert parse_message('s/a/b') == (None, 'a', 'b', [])
    assert parse_message('nick:s/a/b') == ('nick', 'a', 'b', [])
    assert parse_message('nick: s/a/b') == ('nick', 'a', 'b', [])
    assert parse_message('nick: s/lorem ipsum/something else') == ('nick', 'lorem ipsum', 'something else', [])

    assert parse_message('s/a/b/') == (None, 'a', 'b', [])
    assert parse_message('nick:s/a/b/') == ('nick', 'a', 'b', [])
    assert parse_message('nick: s/a/b/') == ('nick', 'a', 'b', [])
    assert parse_message('nick: s/lorem ipsum/something else/') == ('nick', 'lorem ipsum', 'something else', [])

    assert parse_message('s/a/b/gi') == (None, 'a', 'b', ['g', 'i'])
    assert parse_message('nick:s/a/b/gi') == ('nick', 'a', 'b', ['g', 'i'])
    assert parse_message('nick: s/a/b/gi') == ('nick', 'a', 'b', ['g', 'i'])
    assert parse_message('nick: s/lorem ipsum/something else/gi') == ('nick', 'lorem ipsum', 'something else', ['g', 'i'])


def test_parse_message_invalid():
    with pytest.raises(ValueError):
        parse_message('lorem ipsum')
