import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.modules.builtin.news import News


def test_help(make_privmsg, make_incoming_privmsg, unauthorised_context, test_news) -> None:
    msg = make_incoming_privmsg('.help', target='#channel')
    assert test_news.module.get_all_commands(msg, unauthorised_context) == {'help', 'news', 'news_add', 'news_pop', 'news_push', 'news_update'}


def test_news_sequence(test_news, make_incoming_privmsg, unauthorised_context):
    msg = make_incoming_privmsg('.news', target='#channel')
    test_news.receive_auth_message_in(msg, unauthorised_context)
    test_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :There are no news.')
            }
        ]
    )
    test_news.reset_message_out_signals()

    msg = make_incoming_privmsg('.news_add entry 1', target='#channel')
    test_news.receive_auth_message_in(msg, unauthorised_context)
    test_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Ok!')
            }
        ]
    )
    test_news.reset_message_out_signals()

    msg = make_incoming_privmsg('.news_add entry 2', target='#channel')
    test_news.receive_auth_message_in(msg, unauthorised_context)
    test_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Ok!')
            }
        ]
    )
    test_news.reset_message_out_signals()

    msg = make_incoming_privmsg('.news', target='#channel')
    test_news.receive_auth_message_in(msg, unauthorised_context)
    test_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :News 0: entry 2')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :News 1: entry 1')
            }
        ]
    )
    test_news.reset_message_out_signals()

    msg = make_incoming_privmsg('.news_update 0 updated entry 2', target='#channel')
    test_news.receive_auth_message_in(msg, unauthorised_context)
    test_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Ok!')
            }
        ]
    )
    test_news.reset_message_out_signals()

    msg = make_incoming_privmsg('.news', target='#channel')
    test_news.receive_auth_message_in(msg, unauthorised_context)
    test_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :News 0: updated entry 2')
            },
            {
                'msg': Message.new_from_string('PRIVMSG #channel :News 1: entry 1')
            }
        ]
    )
    test_news.reset_message_out_signals()

    msg = make_incoming_privmsg('.news_pop 1', target='#channel')
    test_news.receive_auth_message_in(msg, unauthorised_context)
    test_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Ok!')
            }
        ]
    )
    test_news.reset_message_out_signals()

    msg = make_incoming_privmsg('.news', target='#channel')
    test_news.receive_auth_message_in(msg, unauthorised_context)
    test_news.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :News 0: updated entry 2')
            }
        ]
    )


@pytest.fixture()
def test_news(module_harness_factory, tmp_file):
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
