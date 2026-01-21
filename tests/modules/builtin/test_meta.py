from botnet.message import Message
from botnet.config import Config
from botnet.modules.builtin.meta import Meta


def make_config():
    config = {'module_config': {'botnet': {'base_responder': {'command_prefix': ':'}}}}
    return Config(config)


def test_help(module_harness_factory, unauthorised_context, make_privmsg):
    m = module_harness_factory.make(Meta, make_config())

    msg = make_privmsg(':help')
    m.receive_auth_message_in(msg, unauthorised_context)
    m.expect_request_list_commands_signals(
        [
            {
                'msg': msg,
                'auth': unauthorised_context,
            }
        ]
    )


def test_bots(module_harness_factory, make_privmsg):
    m = module_harness_factory.make(Meta, make_config())

    m.receive_message_in(make_privmsg('.bots'))
    m.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Reporting in! [Python] https://github.com/boreq/botnet try :help (https://ibip.0x46.net/)')
            }
        ]
    )


def test_git(module_harness_factory, unauthorised_context, make_privmsg):
    m = module_harness_factory.make(Meta, make_config())

    m.receive_auth_message_in(make_privmsg(':git'), unauthorised_context)
    m.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Reporting in! [Python] https://github.com/boreq/botnet try :help (https://ibip.0x46.net/)')
            }
        ]
    )
