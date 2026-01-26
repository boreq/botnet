from botnet.codes import Code
from botnet.message import Channel
from botnet.message import IncomingPrivateMessage
from botnet.message import Message
from botnet.message import Nick
from botnet.message import Target
from botnet.message import Text


def test_message_from_string(subtests):
    test_cases = [
        {
            'string': ':irc.example.com 251 botnet_test :There are 185 users on 25 servers',

            'prefix': 'irc.example.com',
            'command': '251',
            'params': ['botnet_test', 'There are 185 users on 25 servers'],

            'servername': 'irc.example.com',
            'nickname': None,

            'command_code': Code.RPL_LUSERCLIENT,
        },
        {
            'string': ':nick!~user@11-222-333-44.example.com PRIVMSG #channel :test 123456',

            'prefix': 'nick!~user@11-222-333-44.example.com',
            'command': 'PRIVMSG',
            'params': ['#channel', 'test 123456'],

            'servername': None,
            'nickname': 'nick',

            'command_code': None,
        },
        {
            # I think this is some kind of a message that contains non-stanard control sequences?
            # I presume this blew something up in the past?
            'string': bytes.fromhex('3a6e 6963 6b21 7e7a 401f 0334 4a6f 796f 7573 032e 0333 4b77 616e 7a61 6103 2e1f 6e69 636b 2050 5249 564d 5347 2072 6f62 6f74 6e65 745f 7465 7374 2074 6573 74').decode(),

            'prefix': 'nick!~z@\x1f\x034Joyous\x03.\x033Kwanzaa\x03.\x1fnick',
            'command': 'PRIVMSG',
            'params': ['robotnet_test', 'test'],

            'servername': None,
            'nickname': 'nick',

            'command_code': None,
        },
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            msg = Message.new_from_string(test_case['string'])
            assert msg.prefix == test_case['prefix']
            assert msg.command == test_case['command']
            assert msg.params == test_case['params']
            assert msg.servername == test_case['servername']
            assert msg.nickname == test_case['nickname']
            assert msg.command_code == test_case['command_code']
            assert msg.to_string() == test_case['string']


def test_message_to_string(subtests):
    test_cases = [
        {
            'prefix': None,
            'command': 'PRIVMSG',
            'params': ['#channel', 'message'],
            'expected_message': 'PRIVMSG #channel message',
        },
        {
            'prefix': 'prefix',
            'command': 'PRIVMSG',
            'params': ['#channel', 'message'],
            'expected_message': ':prefix PRIVMSG #channel message',
        },
        {
            'prefix': 'prefix',
            'command': 'PRIVMSG',
            'params': ['#channel', 'message with spaces'],
            'expected_message': ':prefix PRIVMSG #channel :message with spaces',
        },
        {
            'prefix': 'prefix',
            'command': 'PRIVMSG',
            'params': ['#channel', '.command'],
            'expected_message': ':prefix PRIVMSG #channel .command',
        },
        {
            'prefix': 'prefix',
            'command': 'PRIVMSG',
            'params': ['#channel', ':command'],
            'expected_message': ':prefix PRIVMSG #channel ::command',
        },
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            msg = Message(prefix=test_case['prefix'], command=test_case['command'], params=test_case['params'])
            assert msg.to_string() == test_case['expected_message']


def test_nick(subtests):
    test_cases = [
        {
            'nick': 'nick',
            'error': None,
        },
        {
            'nick': 'nick|m',
            'error': None,
        },
        {
            'nick': 'nick-m',
            'error': None,
        },
        {
            'nick': 'nick_m',
            'error': None,
        },
        {
            'nick': 'nick0m',
            'error': None,
        },
        {
            'nick': 'n',
            'error': None,
        },
        {
            'nick': None,
            'error': 'nick cannot be none or empty',
        },
        {
            'nick': '',
            'error': 'nick cannot be none or empty',
        },
        {
            'nick': '@nick',
            'error': 'nick \'@nick\' is invalid',
        },
        {
            'nick': '+nick',
            'error': 'nick \'+nick\' is invalid',
        },
        {
            'nick': '|nick',
            'error': 'nick \'|nick\' is invalid',
        },
        {
            'nick': '-nick',
            'error': 'nick \'-nick\' is invalid',
        },
        {
            'nick': '_nick',
            'error': None,
        },
        {
            'nick': '0nick',
            'error': 'nick \'0nick\' is invalid',
        },
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            try:
                nick = Nick(test_case['nick'])
                if test_case['error'] is not None:
                    raise Exception('error expected')
                else:
                    assert nick.s == test_case['nick']
            except Exception as e:
                if test_case['error'] is not None:
                    assert str(e) == test_case['error']
                else:
                    raise


def test_nick_is_not_case_sensitive(subtests):
    assert Nick('a') != Nick('b')
    assert hash(Nick('a')) != hash(Nick('b'))

    assert Nick('test') == Nick('test')
    assert hash(Nick('test')) == hash(Nick('test'))

    assert Nick('test') == Nick('TEST')
    assert hash(Nick('test')) == hash(Nick('TEST'))


def test_channel(subtests):
    test_cases = [
        {
            'channel': '#channel',
            'error': None,
        },
        {
            'channel': '##channel',
            'error': None,
        },
        {
            'channel': 'channel',
            'error': 'channel \'channel\' is invalid',
        },
        {
            'channel': 'c#hannel',
            'error': 'channel \'c#hannel\' is invalid',
        },
        {
            'channel': '',
            'error': 'channel cannot be none or empty',
        },
        {
            'channel': None,
            'error': 'channel cannot be none or empty',
        },
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            try:
                nick = Channel(test_case['channel'])
                if test_case['error'] is not None:
                    raise Exception('error expected')
                else:
                    assert nick.s == test_case['channel']
            except Exception as e:
                if test_case['error'] is not None:
                    assert str(e) == test_case['error']
                else:
                    raise


def test_channel_is_not_case_sensitive(subtests):
    assert Channel('#a') != Channel('#b')
    assert hash(Channel('#a')) != hash(Channel('#b'))

    assert Channel('#test') == Channel('#test')
    assert hash(Channel('#test')) == hash(Channel('#test'))

    assert Channel('#test') == Channel('#TEST')
    assert hash(Channel('#test')) == hash(Channel('#TEST'))


def test_target(subtests):
    test_cases = [
        {
            'target': '#channel',
            'channel': True,
        },
        {
            'target': 'nick',
            'channel': False,
        },
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            target = Target.new_from_string(test_case['target'])
            if test_case['channel']:
                assert target.is_channel
                assert not target.is_nick
                assert target.channel is not None
                assert target.nick is None
            else:
                assert not target.is_channel
                assert target.is_nick
                assert target.channel is None
                assert target.nick is not None


def test_text(subtests):
    test_cases = [
        {
            'text': 'message text',
            'error': None,
        },
        {
            'text': '',
            'error': 'text cannot be none or empty',
        },
        {
            'text': None,
            'error': 'text cannot be none or empty',
        },
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            try:
                text = Text(test_case['text'])
                if test_case['error'] is not None:
                    raise Exception('error expected')
                else:
                    assert text.s == test_case['text']
            except Exception as e:
                if test_case['error'] is not None:
                    assert str(e) == test_case['error']
                else:
                    raise


def test_incoming_private_message_from_message():
    msg = Message(command='PRIVMSG', prefix='nick!~user@example.com', params=['#channel', 'message text'])
    ipm = IncomingPrivateMessage.new_from_message(msg)
    assert ipm.sender == Nick('nick')
    assert ipm.target == Target(Channel('#channel'))
    assert ipm.text == Text('message text')
