import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.modules.builtin.sed import MsgEntry
from botnet.modules.builtin.sed import Sed
from botnet.modules.builtin.sed import parse_message
from botnet.modules.builtin.sed import replace

from ...conftest import MakePrivmsgFixture


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
        MsgEntry('nick', 'lorem ipsum lorem'),
    ]
    assert replace(messages, *parse_message('nick: s/lorem/test')) == 'test ipsum lorem'


def test_replace_multiple():
    messages = [
        MsgEntry('nick', 'lorem ipsum one'),
        MsgEntry('nick', 'lorem ipsum two'),
    ]
    assert replace(messages, *parse_message('nick: s/lorem/test')) == 'test ipsum one'


def test_replace_global():
    messages = [
        MsgEntry('nick', 'lorem ipsum lorem'),
    ]
    assert replace(messages, *parse_message('nick: s/lorem/test/g')) == 'test ipsum test'


def test_same_channel(make_privmsg: MakePrivmsgFixture, unauthorised_context, tested_sed):
    msg = make_privmsg('Hellp!', nick='author', target='#channel')
    tested_sed.receive_message_in(msg)

    msg = make_privmsg('s/Hellp!/Hello!', nick='author', target='#channel')
    tested_sed.receive_message_in(msg)

    tested_sed.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :author meant to say: Hello!')
            }
        ]
    )


@pytest.fixture()
def tested_sed(module_harness_factory, tmp_file):
    with open(tmp_file, 'w', encoding='utf-8') as f:
        f.write('{}')

    config = {
        'module_config': {
            'botnet': {
                'sed': {
                    'message_data': tmp_file,
                }
            }
        }
    }

    return module_harness_factory.make(Sed, Config(config))
