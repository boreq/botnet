import pytest
from botnet.modules.builtin.sed import parse_message, make_msg_entry, replace


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


def test_replace_single():
    messages = [
        make_msg_entry('nick', 'lorem ipsum lorem'),
    ]
    assert replace(messages, *parse_message('nick: s/lorem/test')) == 'test ipsum lorem'


def test_replace_multiple():
    messages = [
        make_msg_entry('nick', 'lorem ipsum one'),
        make_msg_entry('nick', 'lorem ipsum two'),
    ]
    assert replace(messages, *parse_message('nick: s/lorem/test')) == 'test ipsum one'


def test_replace_global():
    messages = [
        make_msg_entry('nick', 'lorem ipsum lorem'),
    ]
    assert replace(messages, *parse_message('nick: s/lorem/test/g')) == 'test ipsum test'
