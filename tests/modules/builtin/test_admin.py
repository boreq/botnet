import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.modules.builtin.admin import Admin

from ...conftest import MakePrivmsgFixture


def test_help(make_privmsg: MakePrivmsgFixture, admin_context, tested_admin) -> None:
    msg = make_privmsg('.help', target='#channel')
    assert tested_admin.module.get_all_commands(msg, admin_context) == {
        'help', 'module_load', 'module_unload', 'module_reload', 'config_reload'
    }


def test_module_load(make_privmsg: MakePrivmsgFixture, admin_context, tested_admin):
    msg = make_privmsg('.module_load module1 module2', target='#channel')
    tested_admin.receive_auth_message_in(msg, admin_context)

    tested_admin.expect_module_load_signals([
        {'module_name': 'module1'},
        {'module_name': 'module2'}
    ])

    tested_admin.send_module_loaded(type('Module1', (), {}))
    tested_admin.send_module_loaded(type('Module2', (), {}))

    tested_admin.expect_message_out_signals([
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Loaded module tests.modules.builtin.test_admin.Module1")
        },
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Loaded module tests.modules.builtin.test_admin.Module2")
        }
    ])


def test_module_unload(make_privmsg: MakePrivmsgFixture, admin_context, tested_admin):
    msg = make_privmsg('.module_unload module1', target='#channel')
    tested_admin.receive_auth_message_in(msg, admin_context)

    tested_admin.expect_module_unload_signals([
        {'module_name': 'module1'}
    ])

    tested_admin.send_module_unloaded(type('Module1', (), {}))

    tested_admin.expect_message_out_signals([
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Unloaded module tests.modules.builtin.test_admin.Module1")
        }
    ])


def test_module_reload(make_privmsg: MakePrivmsgFixture, admin_context, tested_admin):
    msg = make_privmsg('.module_reload module1', target='#channel')
    tested_admin.receive_auth_message_in(msg, admin_context)

    tested_admin.expect_module_unload_signals([
        {'module_name': 'module1'}
    ])
    tested_admin.expect_module_load_signals([
        {'module_name': 'module1'}
    ])

    tested_admin.send_module_unloaded(type('Module1', (), {}))
    tested_admin.send_module_loaded(type('Module1', (), {}))

    tested_admin.expect_message_out_signals([
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Unloaded module tests.modules.builtin.test_admin.Module1")
        },
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Loaded module tests.modules.builtin.test_admin.Module1")
        }
    ])


def test_config_reload(make_privmsg: MakePrivmsgFixture, admin_context, tested_admin):
    msg = make_privmsg('.config_reload', target='#channel')
    tested_admin.receive_auth_message_in(msg, admin_context)

    tested_admin.expect_config_reload_signals([
        {}
    ])

    tested_admin.send_config_reloaded()

    tested_admin.expect_message_out_signals([
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Config reloaded")
        }
    ])


@pytest.fixture()
def tested_admin(module_harness_factory):
    return module_harness_factory.make(Admin, Config())
