import os

from botnet.config import Config
from botnet.message import Message
from botnet.modules.builtin.quotes import Quotes
from botnet.modules.builtin.quotes import QuotesConfig

from ...conftest import MakePrivmsgFixture


def test_quotes(module_harness_factory, make_privmsg: MakePrivmsgFixture):
    dirname = os.path.dirname(os.path.realpath(__file__))
    filename = os.path.join(dirname, '..', '..', 'resources', 'quotes')

    config = Config({
        'module_config': {
            'botnet': {
                'quotes': {
                    'directories': [],
                    'files': {}
                }
            }
        }
    })

    m = module_harness_factory.make(Quotes, Config(config))

    msg = make_privmsg('.lotr')
    m.receive_message_in(msg)
    m.expect_message_out_signals([])

    def add_file_to_config(config: QuotesConfig) -> None:
        config.files['lotr'] = filename
    m.module.change_config(add_file_to_config)

    m.receive_message_in(msg)
    m.expect_message_out_signals(
        [
            {
                'msg': Message.new_from_string('PRIVMSG #channel :Three Rings for the Elven-kings under the sky')
            }
        ]
    )
