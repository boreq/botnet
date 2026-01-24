import pytest
from botnet.modules.builtin.sed import Sed, parse_message, make_msg_entry, replace
from botnet.config import Config
from botnet.message import Message


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


def test_same_channel(make_privmsg, make_incoming_privmsg, unauthorised_context, test_sed):
    msg = make_privmsg('Hellp!', nick='author', target='#channel')
    test_sed.receive_message_in(msg)

    msg = make_privmsg('s/Hellp!/Hello!', nick='author', target='#channel')
    test_sed.receive_message_in(msg)

    test_sed.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :author meant to say: Hello!')
            }
        ]
    )


@pytest.fixture()
def test_sed(module_harness_factory, tmp_file):
    class TestSed(Sed):

        def __init__(self, *args, **kwargs):
            self.default_config = {
                'message_data': tmp_file,
            }
            super().__init__(*args, **kwargs)

    return module_harness_factory.make(TestSed, Config())
