from botnet.config import Config
from botnet.message import Channel
from botnet.message import IncomingPrivateMessage
from botnet.message import Message
from botnet.message import Nick
from botnet.message import Target
from botnet.message import Text
from botnet.modules import BaseResponder


def test_respond(subtests, module_harness_factory):
    """Test if BaseResponder.respond sends messages to proper targets."""
    test_cases = [
        {
            'message_target': '#channel',
            'pm': False,
            'expected': 'PRIVMSG #channel :some response',
        },
        {
            'message_target': 'bot_nick',
            'pm': False,
            'expected': 'PRIVMSG nick :some response',
        },
        {
            'message_target': '#channel',
            'pm': True,
            'expected': 'PRIVMSG nick :some response',
        },
        {
            'message_target': 'bot_nick',
            'pm': True,
            'expected': 'PRIVMSG nick :some response',
        },
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            msg = IncomingPrivateMessage(
                sender=Nick('nick'),
                target=Target.new_from_string(test_case['message_target']),
                text=Text('some text'),
            )

            m = module_harness_factory.make(BaseResponder, Config())
            m.module.respond(msg, 'some response', pm=test_case['pm'])

            m.expect_message_out_signals(
                [
                    {
                        'msg': Message.new_from_string(test_case['expected'])
                    }
                ]
            )


def test_get_command_name(subtests):
    test_cases = [
        {
            'text': '.test',
            'expected': 'test',
        },
        {
            'text': '.test arg',
            'expected': 'test',
        },
        {
            'text': ':test',
            'expected': None,
        },
        {
            'text': ':test arg',
            'expected': None,
        },
        {
            'text': 'test',
            'expected': None,
        },
        {
            'text': 'test arg',
            'expected': None,
        },
        {
            'text': ':',
            'expected': None,
        },
        {
            'text': '.',
            'expected': None,
        },
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            msg = IncomingPrivateMessage(
                sender=Nick('nick'),
                target=Target(Channel('#channel')),
                text=Text(test_case['text']),
            )

            r = BaseResponder(Config())
            assert r.get_command_name(msg) == test_case['expected']
