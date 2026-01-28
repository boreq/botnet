from dataclasses import dataclass

from botnet.codes import Code
from botnet.message import Channel
from botnet.message import IncomingJoin
from botnet.message import IncomingKick
from botnet.message import IncomingPart
from botnet.message import IncomingPrivateMessage
from botnet.message import IncomingQuit
from botnet.message import Message
from botnet.message import Nick
from botnet.message import Target
from botnet.message import Text


def test_message_from_string(subtests):
    @dataclass
    class TestCase:
        string: str
        prefix: str | None
        command: str
        params: list[str]
        servername: str | None
        nickname: str | None
        command_code: Code | None

    test_cases = [
        TestCase(
            string=':irc.example.com 251 botnet_test :There are 185 users on 25 servers',
            prefix='irc.example.com',
            command='251',
            params=['botnet_test', 'There are 185 users on 25 servers'],
            servername='irc.example.com',
            nickname=None,
            command_code=Code.RPL_LUSERCLIENT,
        ),
        TestCase(
            string=':nick!~user@11-222-333-44.example.com PRIVMSG #channel :test 123456',
            prefix='nick!~user@11-222-333-44.example.com',
            command='PRIVMSG',
            params=['#channel', 'test 123456'],
            servername=None,
            nickname='nick',
            command_code=None,
        ),
        TestCase(
            string=bytes.fromhex('3a6e 6963 6b21 7e7a 401f 0334 4a6f 796f 7573 032e 0333 4b77 616e 7a61 6103 2e1f 6e69 636b 2050 5249 564d 5347 2072 6f62 6f74 6e65 745f 7465 7374 2074 6573 74').decode(),
            prefix='nick!~z@\x1f\x034Joyous\x03.\x033Kwanzaa\x03.\x1fnick',
            command='PRIVMSG',
            params=['robotnet_test', 'test'],
            servername=None,
            nickname='nick',
            command_code=None,
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            msg = Message.new_from_string(test_case.string)
            assert msg.prefix == test_case.prefix
            assert msg.command == test_case.command
            assert msg.params == test_case.params
            assert msg.servername == test_case.servername
            assert msg.nickname == test_case.nickname
            assert msg.command_code == test_case.command_code
            assert msg.to_string() == test_case.string


def test_message_to_string(subtests):
    @dataclass
    class TestCase:
        prefix: str | None
        command: str
        params: list[str]
        expected_message: str

    test_cases = [
        TestCase(
            prefix=None,
            command='PRIVMSG',
            params=['#channel', 'message'],
            expected_message='PRIVMSG #channel message',
        ),
        TestCase(
            prefix='prefix',
            command='PRIVMSG',
            params=['#channel', 'message'],
            expected_message=':prefix PRIVMSG #channel message',
        ),
        TestCase(
            prefix='prefix',
            command='PRIVMSG',
            params=['#channel', 'message with spaces'],
            expected_message=':prefix PRIVMSG #channel :message with spaces',
        ),
        TestCase(
            prefix='prefix',
            command='PRIVMSG',
            params=['#channel', '.command'],
            expected_message=':prefix PRIVMSG #channel .command',
        ),
        TestCase(
            prefix='prefix',
            command='PRIVMSG',
            params=['#channel', ':command'],
            expected_message=':prefix PRIVMSG #channel ::command',
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            msg = Message(prefix=test_case.prefix, command=test_case.command, params=test_case.params)
            assert msg.to_string() == test_case.expected_message


def test_nick(subtests):
    @dataclass
    class TestCase:
        nick: str | None
        error: str | None

    test_cases = [
        TestCase(
            nick='nick',
            error=None,
        ),
        TestCase(
            nick='nick|m',
            error=None,
        ),
        TestCase(
            nick='nick-m',
            error=None,
        ),
        TestCase(
            nick='nick_m',
            error=None,
        ),
        TestCase(
            nick='nick0m',
            error=None,
        ),
        TestCase(
            nick='n',
            error=None,
        ),
        TestCase(
            nick=None,
            error='nick cannot be none or empty',
        ),
        TestCase(
            nick='',
            error='nick cannot be none or empty',
        ),
        TestCase(
            nick='@nick',
            error='nick \'@nick\' is invalid',
        ),
        TestCase(
            nick='+nick',
            error='nick \'+nick\' is invalid',
        ),
        TestCase(
            nick='|nick',
            error='nick \'|nick\' is invalid',
        ),
        TestCase(
            nick='-nick',
            error='nick \'-nick\' is invalid',
        ),
        TestCase(
            nick='_nick',
            error=None,
        ),
        TestCase(
            nick='0nick',
            error='nick \'0nick\' is invalid',
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            try:
                nick = Nick(test_case.nick)
                if test_case.error is not None:
                    raise Exception('error expected')
                else:
                    assert nick.s == test_case.nick
            except Exception as e:
                if test_case.error is not None:
                    assert str(e) == test_case.error
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
    @dataclass
    class TestCase:
        channel: str | None
        error: str | None

    test_cases = [
        TestCase(
            channel='#channel',
            error=None,
        ),
        TestCase(
            channel='##channel',
            error=None,
        ),
        TestCase(
            channel='channel',
            error='channel \'channel\' is invalid',
        ),
        TestCase(
            channel='c#hannel',
            error='channel \'c#hannel\' is invalid',
        ),
        TestCase(
            channel='',
            error='channel cannot be none or empty',
        ),
        TestCase(
            channel=None,
            error='channel cannot be none or empty',
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            try:
                nick = Channel(test_case.channel)
                if test_case.error is not None:
                    raise Exception('error expected')
                else:
                    assert nick.s == test_case.channel
            except Exception as e:
                if test_case.error is not None:
                    assert str(e) == test_case.error
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
    @dataclass
    class TestCase:
        target: str
        channel: bool

    test_cases = [
        TestCase(
            target='#channel',
            channel=True,
        ),
        TestCase(
            target='nick',
            channel=False,
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            target = Target.new_from_string(test_case.target)
            if test_case.channel:
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
    @dataclass
    class TestCase:
        text: str | None
        error: str | None

    test_cases = [
        TestCase(
            text='message text',
            error=None,
        ),
        TestCase(
            text='',
            error='text cannot be none or empty',
        ),
        TestCase(
            text=None,
            error='text cannot be none or empty',
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            try:
                text = Text(test_case.text)
                if test_case.error is not None:
                    raise Exception('error expected')
                else:
                    assert text.s == test_case.text
            except Exception as e:
                if test_case.error is not None:
                    assert str(e) == test_case.error
                else:
                    raise


def test_incoming_private_message_from_message():
    msg = Message(command='PRIVMSG', prefix='nick!~user@example.com', params=['#channel', 'message text'])
    ipm = IncomingPrivateMessage.new_from_message(msg)
    assert ipm.sender == Nick('nick')
    assert ipm.target == Target(Channel('#channel'))
    assert ipm.text == Text('message text')


def test_incoming_join_from_message(subtests):
    @dataclass
    class TestCase:
        string: str
        expected: IncomingJoin

    test_cases = [
        TestCase(
            string=':nick!user@host JOIN #channel',
            expected=IncomingJoin(Nick('nick'), Channel('#channel')),
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            msg = Message.new_from_string(test_case.string)
            ij = IncomingJoin.new_from_message(msg)
            assert ij == test_case.expected


def test_incoming_part_from_message(subtests):
    @dataclass
    class TestCase:
        string: str
        expected: IncomingPart

    test_cases = [
        TestCase(
            string=':nick!user@host PART #channel',
            expected=IncomingPart(Nick('nick'), Channel('#channel'), None),
        ),
        TestCase(
            string=':nick!user@host PART #channel :Part message',
            expected=IncomingPart(Nick('nick'), Channel('#channel'), 'Part message'),
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            msg = Message.new_from_string(test_case.string)
            ip = IncomingPart.new_from_message(msg)
            assert ip == test_case.expected


def test_incoming_quit_from_message(subtests):
    @dataclass
    class TestCase:
        string: str
        expected: IncomingQuit

    test_cases = [
        TestCase(
            string=':nick!user@host QUIT',
            expected=IncomingQuit(Nick('nick'), None),
        ),
        TestCase(
            string=':nick!user@host QUIT :Quit message',
            expected=IncomingQuit(Nick('nick'), 'Quit message'),
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            msg = Message.new_from_string(test_case.string)
            iq = IncomingQuit.new_from_message(msg)
            assert iq == test_case.expected


def test_incoming_kick_from_message(subtests):
    @dataclass
    class TestCase:
        string: str
        expected: IncomingKick

    test_cases = [
        TestCase(
            string=':kicker!user@host KICK #channel kickee',
            expected=IncomingKick(Nick('kicker'), Channel('#channel'), Nick('kickee'), None),
        ),
        TestCase(
            string=':kicker!user@host KICK #channel kickee :Kick reason',
            expected=IncomingKick(Nick('kicker'), Channel('#channel'), Nick('kickee'), 'Kick reason'),
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            msg = Message.new_from_string(test_case.string)
            ik = IncomingKick.new_from_message(msg)
            assert ik == test_case.expected
