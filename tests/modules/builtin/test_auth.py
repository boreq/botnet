from dataclasses import dataclass
from typing import Callable

import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.message import Nick
from botnet.modules import AuthContext
from botnet.modules.builtin.auth import Auth
from botnet.modules.builtin.auth import AuthorisedGroup
from botnet.modules.builtin.auth import AuthorisedUser
from botnet.modules.builtin.auth import WhoisResponse
from botnet.signals import with_group as with_group_signal
from botnet.signals import with_user as with_user_signal
from tests.conftest import ModuleHarnessFactory

from ...conftest import ModuleHarness


def test_whois_parsing(subtests: pytest.Subtests, make_tested_auth: Callable[[], ModuleHarness[Auth]]) -> None:
    @dataclass
    class TestCase:
        nick: str
        messages: list[str]
        result: WhoisResponse

    test_cases = [
        # hackint irc
        TestCase(
            nick='nick1',
            messages=[
                ':vindobona.hackint.org 311 target_nick nick1 ~user hackint/user/username * :real name',
                ':vindobona.hackint.org 319 target_nick nick1 :@#channel1 @#channel2 #channel3',
                ':vindobona.hackint.org 312 target_nick nick1 palermo.hackint.org :The HackINT irc network',
                ':vindobona.hackint.org 671 target_nick nick1 :is using a secure connection',
                ':vindobona.hackint.org 330 target_nick nick1 logged_in_as :is logged in as',
                ':vindobona.hackint.org 318 target_nick nick1 :End of /WHOIS list.',
            ],
            result=WhoisResponse(
                nick='nick1',
                user='~user',
                host='hackint/user/username',
                real_name='real name',
                server='palermo.hackint.org',
                server_info='The HackINT irc network',
                away=None,
                nick_identified='logged_in_as',
            ),
        ),

        # hackint matrix
        TestCase(
            nick='nick2|m',
            messages=[
                ':vindobona.hackint.org 311 robotnet_test nick2|m ~someonemill fd1d:6215:5333::24e * @someone:milliways.info',
                ':vindobona.hackint.org 319 robotnet_test nick2|m :#channel1 #channel2 #channel3',
                ':vindobona.hackint.org 312 robotnet_test nick2|m matrix.hackint.org :local ircd to the matrix bridge',
                ':vindobona.hackint.org 671 robotnet_test nick2|m :is using a secure connection',
                ':vindobona.hackint.org 318 robotnet_test nick2|m :End of /WHOIS list.',
            ],
            result=WhoisResponse(
                nick='nick2|m',
                user='~someonemill',
                host='fd1d:6215:5333::24e',
                real_name='@someone:milliways.info',
                server='matrix.hackint.org',
                server_info='local ircd to the matrix bridge',
                away=None,
                nick_identified=None,
            ),
        ),

        # rizon
        TestCase(
            nick='nick3',
            messages=[
                ':server.example.com 311 target_nick nick3 ~user freebsd/user/username * :real name',
                ':server.example.com 312 target_nick nick3 serv.example.com :Server info',
                ':server.example.com 319 target_nick nick3 #channel1 #channel2',
                ':server.example.com 307 target_nick nick3 :has identified for this nick',
                ':server.example.com 318 target_nick nick3 :End of /WHOIS list.',
            ],
            result=WhoisResponse(
                nick='nick3',
                user='~user',
                host='freebsd/user/username',
                real_name='real name',
                server='serv.example.com',
                server_info='Server info',
                away=None,
                nick_identified='nick3',
            ),
        ),

        # freenode
        TestCase(
            nick='nick4',
            messages=[
                ':server.example.com 311 target_nick nick4 ~user freebsd/user/username * :real name',
                ':server.example.com 312 target_nick nick4 serv.example.com :Server info',
                ':server.example.com 319 target_nick nick4 #channel1 #channel2',
                ':server.example.com 330 target_nick nick4 logged_in_as :is logged in as',
                ':server.example.com 318 target_nick nick4 :End of /WHOIS list.',
            ],
            result=WhoisResponse(
                nick='nick4',
                user='~user',
                host='freebsd/user/username',
                real_name='real name',
                server='serv.example.com',
                server_info='Server info',
                away=None,
                nick_identified='logged_in_as',
            ),
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            tested_auth = make_tested_auth()

            for message_string in test_case.messages:
                tested_auth.receive_message_in(Message.new_from_string(message_string))

            assert not tested_auth.module._whois_current
            data = tested_auth.module._whois_cache.get(Nick(test_case.nick))
            assert data == test_case.result

            tested_auth.stop()


def test_identify_user(subtests: pytest.Subtests, make_tested_auth: Callable[[], ModuleHarness[Auth]]) -> None:
    @dataclass
    class TestCase:
        nick: str
        messages: list[str]
        context: AuthContext

    test_cases = [
        # logged in via hackint irc
        TestCase(
            nick='someone',
            messages=[
                ':vindobona.hackint.org 311 target_nick someone ~user hackint/user/username * :real name',
                ':vindobona.hackint.org 319 target_nick someone :@#channel1 @#channel2 #channel3',
                ':vindobona.hackint.org 312 target_nick someone palermo.hackint.org :The HackINT irc network',
                ':vindobona.hackint.org 671 target_nick someone :is using a secure connection',
                ':vindobona.hackint.org 330 target_nick someone ircnick :is logged in as',
                ':vindobona.hackint.org 318 target_nick someone :End of /WHOIS list.',
            ],
            context=AuthContext('someones_uuid', ['group1', 'group2']),
        ),
        # logged in via hackint irc to a wrong nick
        TestCase(
            nick='someone',
            messages=[
                ':vindobona.hackint.org 311 target_nick someone ~user hackint/user/username * :real name',
                ':vindobona.hackint.org 319 target_nick someone :@#channel1 @#channel2 #channel3',
                ':vindobona.hackint.org 312 target_nick someone palermo.hackint.org :The HackINT irc network',
                ':vindobona.hackint.org 671 target_nick someone :is using a secure connection',
                ':vindobona.hackint.org 330 target_nick someone otherircnick :is logged in as',
                ':vindobona.hackint.org 318 target_nick someone :End of /WHOIS list.',
            ],
            context=AuthContext(None, []),
        ),
        # logged in via hackint matrix
        TestCase(
            nick='someone',
            messages=[
                ':vindobona.hackint.org 311 robotnet_test someone ~someonemill fd1d:6215:5333::24e * @matrixnick:example.com',
                ':vindobona.hackint.org 319 robotnet_test someone :#channel1 #channel2 #channel3',
                ':vindobona.hackint.org 312 robotnet_test someone matrix.hackint.org :local ircd to the matrix bridge',
                ':vindobona.hackint.org 671 robotnet_test someone :is using a secure connection',
                ':vindobona.hackint.org 318 robotnet_test someone :End of /WHOIS list.',
            ],
            context=AuthContext('someones_uuid', ['group1', 'group2']),
        ),
        # logged in via hackint matrix to a wrong nick
        TestCase(
            nick='someone',
            messages=[
                ':vindobona.hackint.org 311 robotnet_test someone ~someonemill fd1d:6215:5333::24e * @othermatrixnick:example.com',
                ':vindobona.hackint.org 319 robotnet_test someone :#channel1 #channel2 #channel3',
                ':vindobona.hackint.org 312 robotnet_test someone matrix.hackint.org :local ircd to the matrix bridge',
                ':vindobona.hackint.org 671 robotnet_test someone :is using a secure connection',
                ':vindobona.hackint.org 318 robotnet_test someone :End of /WHOIS list.',
            ],
            context=AuthContext(None, []),
        ),
        # host and nick
        TestCase(
            nick='hostnick',
            messages=[
                ':vindobona.hackint.org 311 target_nick hostnick ~user 1.2.3.4 * :real name',
                ':vindobona.hackint.org 319 target_nick hostnick :@#channel1 @#channel2 #channel3',
                ':vindobona.hackint.org 312 target_nick hostnick palermo.hackint.org :The HackINT irc network',
                ':vindobona.hackint.org 671 target_nick hostnick :is using a secure connection',
                ':vindobona.hackint.org 318 target_nick hostnick :End of /WHOIS list.',
            ],
            context=AuthContext('someones_uuid', ['group1', 'group2']),
        ),
        # host and nick, invalid host
        TestCase(
            nick='hostnick',
            messages=[
                ':vindobona.hackint.org 311 target_nick hostnick ~user 5.6.7.8 * :real name',
                ':vindobona.hackint.org 319 target_nick hostnick :@#channel1 @#channel2 #channel3',
                ':vindobona.hackint.org 312 target_nick hostnick palermo.hackint.org :The HackINT irc network',
                ':vindobona.hackint.org 671 target_nick hostnick :is using a secure connection',
                ':vindobona.hackint.org 318 target_nick hostnick :End of /WHOIS list.',
            ],
            context=AuthContext(None, []),
        ),
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            tested_auth = make_tested_auth()

            received_msg = Message.new_from_string(f':{test_case.nick}!example.com PRIVMSG #channel :Hello!')
            tested_auth.receive_message_in(received_msg)

            tested_auth.expect_message_out_signals(
                [
                    {
                        'msg': Message.new_from_string(f'WHOIS {test_case.nick}'),
                    },
                ],
            )

            for message_string in test_case.messages:
                tested_auth.receive_message_in(Message.new_from_string(message_string))

            tested_auth.expect_auth_message_in_signals(
                [
                    {
                        'msg': received_msg,
                        'auth': test_case.context,
                    }
                ]
            )

            tested_auth.stop()


def test_cache_invalidation(subtests: pytest.Subtests, make_tested_auth: Callable[[], ModuleHarness[Auth]]) -> None:
    @dataclass
    class TestCase:
        messages: list[str]
        invalidates: bool

    test_cases = [
        TestCase(
            messages=[
                ':someone!example.com QUIT :Client quit',
            ],
            invalidates=True,
        ),
        TestCase(
            messages=[
                ':someone!example.com PART #channel',
            ],
            invalidates=True,
        ),
        TestCase(
            messages=[
                ':admin!example.com KICK #channel someone',
            ],
            invalidates=True,
        ),
        TestCase(
            messages=[
                ':someone!example.com NICK someoneelse',
            ],
            invalidates=True,
        ),
        TestCase(
            messages=[
                ':someoneelse!example.com NICK someone',
            ],
            invalidates=True,
        ),
        TestCase(
            messages=[
                ':someone!example.com PRIVMSG #channel :Hello!',
            ],
            invalidates=False,
        ),
    ]

    whois_response = [
        ':vindobona.hackint.org 311 target_nick someone ~user hackint/user/username * :real name',
        ':vindobona.hackint.org 319 target_nick someone :@#channel1 @#channel2 #channel3',
        ':vindobona.hackint.org 312 target_nick someone palermo.hackint.org :The HackINT irc network',
        ':vindobona.hackint.org 671 target_nick someone :is using a secure connection',
        ':vindobona.hackint.org 330 target_nick someone ircnick :is logged in as',
        ':vindobona.hackint.org 318 target_nick someone :End of /WHOIS list.',
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            tested_auth = make_tested_auth()

            received_msg = Message.new_from_string(':someone!example.com PRIVMSG #channel :Hello!')
            tested_auth.receive_message_in(received_msg)

            tested_auth.expect_message_out_signals(
                [
                    {
                        'msg': Message.new_from_string('WHOIS someone'),
                    },
                ],
            )

            for message_string in whois_response:
                tested_auth.receive_message_in(Message.new_from_string(message_string))

            tested_auth.expect_auth_message_in_signals(
                [
                    {
                        'msg': received_msg,
                        'auth': AuthContext('someones_uuid', ['group1', 'group2']),
                    }
                ]
            )

            for message_string in test_case.messages:
                tested_auth.receive_message_in(Message.new_from_string(message_string))

            tested_auth.reset_message_out_signals()

            received_msg = Message.new_from_string(':someone!example.com PRIVMSG #channel :Hello!')
            tested_auth.receive_message_in(received_msg)

            if test_case.invalidates:
                tested_auth.expect_message_out_signals(
                    [
                        {
                            'msg': Message.new_from_string('WHOIS someone'),
                        },
                    ],
                )
            else:
                tested_auth.expect_message_out_signals(
                    [
                    ],
                )

            tested_auth.stop()


def _whois_response(nick: str, logged_in_as: str | None) -> list[str]:
    messages = [
        f':vindobona.hackint.org 311 target_nick {nick} ~user hackint/user/username * :real name',
        f':vindobona.hackint.org 312 target_nick {nick} palermo.hackint.org :The HackINT irc network',
    ]
    if logged_in_as is not None:
        messages.append(f':vindobona.hackint.org 330 target_nick {nick} {logged_in_as} :is logged in as')
    messages.append(f':vindobona.hackint.org 318 target_nick {nick} :End of /WHOIS list.')
    return messages


def test_with_group_provides_the_members_configured_in_the_group(
    make_tested_auth_with_group: Callable[[], ModuleHarness[Auth]],
) -> None:
    tested_auth = make_tested_auth_with_group()

    groups: list[AuthorisedGroup] = []
    with_group_signal.send(None, group_uuid='admins', with_group=groups.append)

    # the closure runs synchronously, membership comes straight from the config
    assert len(groups) == 1
    assert groups[0].group == 'admins'
    assert [person.uuid for person in groups[0].people] == ['alice_uuid', 'bob_uuid']

    tested_auth.stop()


def test_with_group_messages_only_the_contacts_which_are_identified(
    make_tested_auth_with_group: Callable[[], ModuleHarness[Auth]],
) -> None:
    tested_auth = make_tested_auth_with_group()

    groups: list[AuthorisedGroup] = []
    with_group_signal.send(None, group_uuid='admins', with_group=groups.append)
    groups[0].message_all('hello')

    # nothing is sent before the identity of every contact nick is established
    tested_auth.expect_message_out_signals(
        [
            {'msg': Message.new_from_string('WHOIS alice')},
            {'msg': Message.new_from_string('WHOIS alice_mobile')},
            {'msg': Message.new_from_string('WHOIS bob')},
        ],
    )
    tested_auth.reset_message_out_signals()

    whois_responses = [
        # alice is identified on this nick
        *_whois_response('alice', 'alice_account'),
        # someone else is currently holding this nick of hers
        *_whois_response('alice_mobile', 'mallory_account'),
        # bob is identified on this nick
        *_whois_response('bob', 'bob_account'),
    ]
    for message_string in whois_responses:
        tested_auth.receive_message_in(Message.new_from_string(message_string))

    tested_auth.expect_message_out_signals(
        [
            {'msg': Message.new_from_string('PRIVMSG alice :hello')},
            {'msg': Message.new_from_string('PRIVMSG bob :hello')},
        ],
    )

    tested_auth.stop()


def test_with_group_sends_nothing_if_nobody_is_identified(
    make_tested_auth_with_group: Callable[[], ModuleHarness[Auth]],
) -> None:
    tested_auth = make_tested_auth_with_group()

    groups: list[AuthorisedGroup] = []
    with_group_signal.send(None, group_uuid='admins', with_group=groups.append)
    groups[0].message_all('hello')

    whois_responses = [
        *_whois_response('alice', None),
        *_whois_response('alice_mobile', None),
        *_whois_response('bob', 'someone_else'),
    ]
    for message_string in whois_responses:
        tested_auth.receive_message_in(Message.new_from_string(message_string))

    # the whois lookups are the only thing which was ever sent
    tested_auth.expect_message_out_signals(
        [
            {'msg': Message.new_from_string('WHOIS alice')},
            {'msg': Message.new_from_string('WHOIS alice_mobile')},
            {'msg': Message.new_from_string('WHOIS bob')},
        ],
    )

    tested_auth.stop()


def test_with_user_messages_only_the_contacts_which_are_identified(
    make_tested_auth_with_group: Callable[[], ModuleHarness[Auth]],
) -> None:
    tested_auth = make_tested_auth_with_group()

    def with_user(user: AuthorisedUser) -> None:
        user.message('hello')

    with_user_signal.send(None, user_uuid='alice_uuid', with_user=with_user)

    tested_auth.expect_message_out_signals(
        [
            {'msg': Message.new_from_string('WHOIS alice')},
            {'msg': Message.new_from_string('WHOIS alice_mobile')},
        ],
    )
    tested_auth.reset_message_out_signals()

    whois_responses = [
        *_whois_response('alice', 'alice_account'),
        *_whois_response('alice_mobile', 'mallory_account'),
    ]
    for message_string in whois_responses:
        tested_auth.receive_message_in(Message.new_from_string(message_string))

    tested_auth.expect_message_out_signals(
        [
            {'msg': Message.new_from_string('PRIVMSG alice :hello')},
        ],
    )

    tested_auth.stop()


@pytest.fixture()
def make_tested_auth_with_group(module_harness_factory: ModuleHarnessFactory) -> Callable[[], ModuleHarness[Auth]]:
    config = Config(
        {
            'module_config': {
                'botnet': {
                    'auth': {
                        'people': [
                            {
                                'uuid': 'alice_uuid',
                                'authorisations': [
                                    {
                                        'logged_in_as': {
                                            'nick': 'alice_account',
                                        }
                                    },
                                ],
                                'groups': ['admins'],
                                'contact': ['alice', 'alice_mobile'],
                            },
                            {
                                'uuid': 'bob_uuid',
                                'authorisations': [
                                    {
                                        'logged_in_as': {
                                            'nick': 'bob_account',
                                        }
                                    },
                                ],
                                'groups': ['admins'],
                                'contact': ['bob'],
                            },
                            {
                                'uuid': 'carol_uuid',
                                'authorisations': [
                                    {
                                        'logged_in_as': {
                                            'nick': 'carol_account',
                                        }
                                    },
                                ],
                                'groups': ['others'],
                                'contact': ['carol'],
                            },
                        ],
                    },
                },
            },
        }
    )

    return lambda: module_harness_factory.make(Auth, config)


@pytest.fixture()
def make_tested_auth(module_harness_factory: ModuleHarnessFactory) -> Callable[[], ModuleHarness[Auth]]:
    config = Config(
        {
            'module_config': {
                'botnet': {
                    'auth': {
                        'people': [
                            {
                                'uuid': 'someones_uuid',
                                'authorisations': [
                                    {
                                        'logged_in_as': {
                                            'nick': 'ircnick',
                                        }
                                    },
                                    {
                                        'matrix': {
                                            'nick': '@matrixnick:example.com',
                                        }
                                    },
                                    {
                                        'nick_and_host': {
                                            'nick': 'hostnick',
                                            'host': '1.2.3.4',
                                        }
                                    },
                                ],
                                'groups': ['group1', 'group2'],
                                'contact': ['ircnick']
                            },
                        ],
                    },
                },
            },
        }
    )

    return lambda: module_harness_factory.make(Auth, config)
