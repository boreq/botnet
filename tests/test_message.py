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
