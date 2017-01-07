from botnet.message import Message
from botnet.codes import Code


def test_parse1():
    text = ':irc.example.com 251 botnet_test :There are 185 users on 25 servers'
    msg = Message()
    msg.from_string(text)

    # Prefix
    assert msg.prefix == msg.servername == 'irc.example.com'
    assert msg.nickname is None
    # Command
    assert msg.command == '251'
    assert msg.command_code() == Code.RPL_LUSERCLIENT
    # Params
    assert msg.params[0] == 'botnet_test'
    assert msg.params[1] == 'There are 185 users on 25 servers'

    assert msg.to_string() == text


def test_parse2():
    text = ':nick!~user@11-222-333-44.example.com PRIVMSG #channel :test 123456'
    msg = Message()
    msg.from_string(text)

    # Prefix
    assert msg.nickname == 'nick'
    assert msg.servername is None
    # Command
    assert msg.command == 'PRIVMSG'
    assert msg.command_code() is None
    # Params
    assert msg.params[0] == '#channel'
    assert msg.params[1] == 'test 123456'

    assert msg.to_string() == text


def test_parse_pretty_illegal_colors():
    text = bytes.fromhex('3a6e 6963 6b21 7e7a 401f 0334 4a6f 796f 7573 032e 0333 4b77 616e 7a61 6103 2e1f 6e69 636b 2050 5249 564d 5347 2072 6f62 6f74 6e65 745f 7465 7374 2074 6573 74').decode()
    msg = Message()
    msg.from_string(text)

    # Prefix
    assert msg.nickname == 'nick'
    assert msg.servername is None
    # Command
    assert msg.command == 'PRIVMSG'
    assert msg.command_code() is None
    # Params
    print(msg.params)
    assert msg.params[0] == 'robotnet_test'
    assert msg.params[1] == 'test'

    assert msg.to_string() == text


def test_build1():
    prefix = 'prefix'
    command = 'command'
    params = ['param1', 'param2']
    text = ':prefix COMMAND param1 param2'

    msg = Message(prefix=prefix, command=command, params=params)
    assert msg.to_string() == text


def test_build2():
    command = 'command'
    params = ['param1', 'param with spaces']
    text = 'COMMAND param1 :param with spaces'

    msg = Message(command=command, params=params)
    assert msg.to_string() == text
