import os
from botnet.message import Message
from botnet.config import Config
from botnet.modules.builtin.quotes import Quotes


def test_quotes(module_harness_factory, make_privmsg):
    dirname = os.path.dirname(os.path.realpath(__file__))
    filename = os.path.join(dirname, 'quotes')

    m = module_harness_factory.make(Quotes, Config())

    msg = make_privmsg('.lotr')
    m.receive_message_in(msg)
    m.expect_message_out_signals([])

    m.module.config_set('files.lotr', filename)
    m.receive_message_in(msg)
    m.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Three Rings for the Elven-kings under the sky')
            }
        ]
    )
