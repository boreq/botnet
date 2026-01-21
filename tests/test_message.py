from botnet.message import Message
from botnet.codes import Code


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
