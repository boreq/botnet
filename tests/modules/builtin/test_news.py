import pytest

from botnet.config import Config
from botnet.message import IncomingPrivateMessage
from botnet.message import Message
from botnet.modules.builtin.news import News

from ...conftest import MakePrivmsgFixture


def test_help(make_privmsg: MakePrivmsgFixture, unauthorised_context, tested_news) -> None:
    msg = IncomingPrivateMessage.new_from_message(make_privmsg('.help', target='#channel'))
    assert tested_news.module.get_all_commands(msg, unauthorised_context) == {'help', 'news', 'news_add', 'news_pop', 'news_push', 'news_update'}


def test_news_sequence(tested_news, make_privmsg: MakePrivmsgFixture, unauthorised_context):
    msg = make_privmsg('.news', target='#channel')
    tested_news.receive_auth_message_in(msg, unauthorised_context)
    tested_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :There are no news.')
            }
        ]
    )
    tested_news.reset_message_out_signals()

    msg = make_privmsg('.news_add entry 1', target='#channel')
    tested_news.receive_auth_message_in(msg, unauthorised_context)
    tested_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Ok!')
            }
        ]
    )
    tested_news.reset_message_out_signals()

    msg = make_privmsg('.news_add entry 2', target='#channel')
    tested_news.receive_auth_message_in(msg, unauthorised_context)
    tested_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Ok!')
            }
        ]
    )
    tested_news.reset_message_out_signals()

    msg = make_privmsg('.news', target='#channel')
    tested_news.receive_auth_message_in(msg, unauthorised_context)
    tested_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :News 0: entry 2')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :News 1: entry 1')
            }
        ]
    )
    tested_news.reset_message_out_signals()

    msg = make_privmsg('.news_update 0 updated entry 2', target='#channel')
    tested_news.receive_auth_message_in(msg, unauthorised_context)
    tested_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Ok!')
            }
        ]
    )
    tested_news.reset_message_out_signals()

    msg = make_privmsg('.news', target='#channel')
    tested_news.receive_auth_message_in(msg, unauthorised_context)
    tested_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :News 0: updated entry 2')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :News 1: entry 1')
            }
        ]
    )
    tested_news.reset_message_out_signals()

    msg = make_privmsg('.news_pop 1', target='#channel')
    tested_news.receive_auth_message_in(msg, unauthorised_context)
    tested_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Ok!')
            }
        ]
    )
    tested_news.reset_message_out_signals()

    msg = make_privmsg('.news', target='#channel')
    tested_news.receive_auth_message_in(msg, unauthorised_context)
    tested_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :News 0: updated entry 2')
            }
        ]
    )


@pytest.fixture()
def tested_news(module_harness_factory, tmp_file):
    with open(tmp_file, 'w', encoding='utf-8') as f:
        f.write('{}')

    config = {
        'module_config': {
            'botnet': {
                'news': {
                    'news_data': tmp_file,
                    'channels': ['#channel']
                }
            }
        }
    }

    return module_harness_factory.make(News, Config(config))
