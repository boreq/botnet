import pytest

from botnet.config import Config
from botnet.message import Message
from botnet.modules.builtin.admin import Admin
from tests.conftest import ModuleHarnessFactory


def test_help(make_incoming_privmsg, admin_context, test_admin) -> None:
    msg = make_incoming_privmsg('.help', target='#channel')
    assert test_admin.module.get_all_commands(msg, admin_context) == {
        'help', 'module_load', 'module_unload', 'module_reload', 'config_reload'
    }


def test_module_load(make_incoming_privmsg, admin_context, test_admin):
    msg = make_incoming_privmsg('.module_load module1 module2', target='#channel')
    test_admin.receive_auth_message_in(msg, admin_context)

    test_admin.expect_module_load_signals([
        {'name': 'module1'},
        {'name': 'module2'}
    ])

    test_admin.send_module_loaded(type('Module1', (), {}))
    test_admin.send_module_loaded(type('Module2', (), {}))

    test_admin.expect_message_out_signals([
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Loaded module test_admin.Module1")
        },
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Loaded module test_admin.Module2")
        }
    ])


def test_module_unload(make_incoming_privmsg, admin_context, test_admin):
    msg = make_incoming_privmsg('.module_unload module1', target='#channel')
    test_admin.receive_auth_message_in(msg, admin_context)

    test_admin.expect_module_unload_signals([
        {'name': 'module1'}
    ])

    test_admin.send_module_unloaded(type('Module1', (), {}))

    test_admin.expect_message_out_signals([
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Unloaded module test_admin.Module1")
        }
    ])


def test_module_reload(make_incoming_privmsg, admin_context, test_admin):
    msg = make_incoming_privmsg('.module_reload module1', target='#channel')
    test_admin.receive_auth_message_in(msg, admin_context)

    test_admin.expect_module_unload_signals([
        {'name': 'module1'}
    ])
    test_admin.expect_module_load_signals([
        {'name': 'module1'}
    ])

    test_admin.send_module_unloaded(type('Module1', (), {}))
    test_admin.send_module_loaded(type('Module1', (), {}))

    test_admin.expect_message_out_signals([
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Unloaded module test_admin.Module1")
        },
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Loaded module test_admin.Module1")
        }
    ])


def test_config_reload(make_incoming_privmsg, admin_context, test_admin):
    msg = make_incoming_privmsg('.config_reload', target='#channel')
    test_admin.receive_auth_message_in(msg, admin_context)

    test_admin.expect_config_reload_signals([
        {}
    ])

    test_admin.send_config_reloaded()

    test_admin.expect_message_out_signals([
        {
            'msg': Message.new_from_string("PRIVMSG #channel :Config reloaded")
        }
    ])


@pytest.fixture()
def test_admin(module_harness_factory) -> ModuleHarnessFactory[Admin]:
    return module_harness_factory.make(Admin, Config())
