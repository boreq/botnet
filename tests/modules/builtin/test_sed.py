import pytest
from botnet.modules.builtin.sed import parse_message


def test_parse_message():
    assert parse_message('s/a/b') == (None, 'a', 'b')
    assert parse_message('nick:s/a/b') == ('nick', 'a', 'b')
    assert parse_message('nick: s/a/b') == ('nick', 'a', 'b')
    assert parse_message('nick: s/lorem ipsum/something else') == ('nick', 'lorem ipsum', 'something else')

def test_parse_message():
    with pytest.raises(ValueError):
        parse_message('lorem ipsum')
