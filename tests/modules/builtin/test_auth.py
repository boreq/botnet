from botnet.config import Config
from botnet.modules import AuthContext
from botnet.modules.builtin.auth import Auth
from botnet.message import Message
from botnet.signals import message_out, auth_message_in


def test_whois_parsing(subtests, rec_msg) -> None:
    test_cases = [
        # hackint irc
        {
            'nick': 'nick1',
            'messages': [
                ':vindobona.hackint.org 311 target_nick nick1 ~user hackint/user/username * :real name',
                ':vindobona.hackint.org 319 target_nick nick1 :@#channel1 @#channel2 #channel3',
                ':vindobona.hackint.org 312 target_nick nick1 palermo.hackint.org :The HackINT irc network',
                ':vindobona.hackint.org 671 target_nick nick1 :is using a secure connection',
                ':vindobona.hackint.org 330 target_nick nick1 logged_in_as :is logged in as',
                ':vindobona.hackint.org 318 target_nick nick1 :End of /WHOIS list.',
            ],
            'result': {
                'nick': 'nick1',
                'user': '~user',
                'host': 'hackint/user/username',
                'real_name': 'real name',
                'server': 'palermo.hackint.org',
                'server_info': 'The HackINT irc network',
                'nick_identified': 'logged_in_as',
            },
        },

        # hackint matrix
        {
            'nick': 'nick2|m',
            'messages': [
                ':vindobona.hackint.org 311 robotnet_test nick2|m ~someonemill fd1d:6215:5333::24e * @someone:milliways.info',
                ':vindobona.hackint.org 319 robotnet_test nick2|m :#channel1 #channel2 #channel3',
                ':vindobona.hackint.org 312 robotnet_test nick2|m matrix.hackint.org :local ircd to the matrix bridge',
                ':vindobona.hackint.org 671 robotnet_test nick2|m :is using a secure connection',
                ':vindobona.hackint.org 318 robotnet_test nick2|m :End of /WHOIS list.',
            ],
            'result': {
                'nick': 'nick2|m',
                'user': '~someonemill',
                'host': 'fd1d:6215:5333::24e',
                'real_name': '@someone:milliways.info',
                'server': 'matrix.hackint.org',
                'server_info': 'local ircd to the matrix bridge',
            },
        },

        # rizon
        {
            'nick': 'nick3',
            'messages': [
                ':server.example.com 311 target_nick nick3 ~user freebsd/user/username * :real name',
                ':server.example.com 312 target_nick nick3 serv.example.com :Server info',
                ':server.example.com 319 target_nick nick3 #channel1 #channel2',
                ':server.example.com 307 target_nick nick3 :has identified for this nick',
                ':server.example.com 318 target_nick nick3 :End of /WHOIS list.',
            ],
            'result': {
                'nick': 'nick3',
                'user': '~user',
                'host': 'freebsd/user/username',
                'real_name': 'real name',
                'server': 'serv.example.com',
                'server_info': 'Server info',
                'nick_identified': 'nick3',
            },
        },

        # freenode
        {
            'nick': 'nick4',
            'messages': [
                ':server.example.com 311 target_nick nick4 ~user freebsd/user/username * :real name',
                ':server.example.com 312 target_nick nick4 serv.example.com :Server info',
                ':server.example.com 319 target_nick nick4 #channel1 #channel2',
                ':server.example.com 330 target_nick nick4 logged_in_as :is logged in as',
                ':server.example.com 318 target_nick nick4 :End of /WHOIS list.',
            ],
            'result': {
                'nick': 'nick4',
                'user': '~user',
                'host': 'freebsd/user/username',
                'real_name': 'real name',
                'server': 'serv.example.com',
                'server_info': 'Server info',
                'nick_identified': 'logged_in_as',
            },
        },
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            config: dict = {
                'module_config': {
                    'botnet': {
                        'auth': {}
                    }
                }
            }

            a = Auth(Config(config))

            for message_string in test_case['messages']:
                rec_msg(Message.new_from_string(message_string))

            assert not a._whois_current
            data = a._whois_cache.get(test_case['nick'])
            del data['time']
            assert data == test_case['result']


def test_identify_irc_user(subtests, make_signal_trap, rec_msg):
    config = {
        'module_config': {
            'botnet': {
                'auth': {
                    'people': [
                        {
                            'uuid': 'someones_uuid',
                            'authorisations': [
                                {
                                    'kind': 'irc',
                                    'nick': 'ircnick',
                                },
                                {
                                    'kind': 'matrix',
                                    'nick': '@matrixnick:example.com',
                                },
                            ],
                            'groups': ['group1', 'group2'],
                        },
                    ],
                },
            },
        },
    }

    test_cases = [
        # logged in via hackint irc
        {
            'messages': [
                ':vindobona.hackint.org 311 target_nick someone ~user hackint/user/username * :real name',
                ':vindobona.hackint.org 319 target_nick someone :@#channel1 @#channel2 #channel3',
                ':vindobona.hackint.org 312 target_nick someone palermo.hackint.org :The HackINT irc network',
                ':vindobona.hackint.org 671 target_nick someone :is using a secure connection',
                ':vindobona.hackint.org 330 target_nick someone ircnick :is logged in as',
                ':vindobona.hackint.org 318 target_nick someone :End of /WHOIS list.',
            ],
            'context': AuthContext('someones_uuid', ['group1', 'group2']),
        },
        # logged in via hackint irc to a wrong nick
        {
            'messages': [
                ':vindobona.hackint.org 311 target_nick someone ~user hackint/user/username * :real name',
                ':vindobona.hackint.org 319 target_nick someone :@#channel1 @#channel2 #channel3',
                ':vindobona.hackint.org 312 target_nick someone palermo.hackint.org :The HackINT irc network',
                ':vindobona.hackint.org 671 target_nick someone :is using a secure connection',
                ':vindobona.hackint.org 330 target_nick someone otherircnick :is logged in as',
                ':vindobona.hackint.org 318 target_nick someone :End of /WHOIS list.',
            ],
            'context': AuthContext(None, []),
        },
        # logged in via hackint matrix
        {
            'messages': [
                ':vindobona.hackint.org 311 robotnet_test someone ~someonemill fd1d:6215:5333::24e * @matrixnick:example.com',
                ':vindobona.hackint.org 319 robotnet_test someone :#channel1 #channel2 #channel3',
                ':vindobona.hackint.org 312 robotnet_test someone matrix.hackint.org :local ircd to the matrix bridge',
                ':vindobona.hackint.org 671 robotnet_test someone :is using a secure connection',
                ':vindobona.hackint.org 318 robotnet_test someone :End of /WHOIS list.',
            ],
            'context': AuthContext('someones_uuid', ['group1', 'group2']),
        },
        # logged in via hackint matrix to a wrong nick
        {
            'messages': [
                ':vindobona.hackint.org 311 robotnet_test someone ~someonemill fd1d:6215:5333::24e * @othermatrixnick:example.com',
                ':vindobona.hackint.org 319 robotnet_test someone :#channel1 #channel2 #channel3',
                ':vindobona.hackint.org 312 robotnet_test someone matrix.hackint.org :local ircd to the matrix bridge',
                ':vindobona.hackint.org 671 robotnet_test someone :is using a secure connection',
                ':vindobona.hackint.org 318 robotnet_test someone :End of /WHOIS list.',
            ],
            'context': AuthContext(None, []),
        },
    ]

    for test_case in test_cases:
        with subtests.test(test_case=test_case):
            a = Auth(Config(config))

            message_out_trap = make_signal_trap(message_out)
            auth_message_in_trap = make_signal_trap(auth_message_in)

            received_msg = Message.new_from_string(':someone!example.com PRIVMSG #channel :Hello!')
            rec_msg(received_msg)

            def wait_condition(trapped):
                assert trapped == [{
                    'msg': Message.new_from_string('WHOIS someone'),
                }]
            message_out_trap.wait(wait_condition)

            for message_string in test_case['messages']:
                rec_msg(Message.new_from_string(message_string))

            def wait_condition(trapped):
                assert trapped == [{
                    'msg': received_msg,
                    'auth': test_case['context'],
                }]
            auth_message_in_trap.wait(wait_condition)

            a.stop()
