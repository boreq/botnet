import time
from botnet.config import Config


def make_admin_config(command_prefix='.'):
    config = {
        'module_config': {
            'botnet': {
                'admin': {
                    'admins': [
                        'nick4'
                    ]
                }
            }
        }
    }
    config = Config(config)
    return config


def test_reload_meta(cl, msg_l, make_privmsg, rec_msg):
    """Load, send, unload, send, load, send."""
    from botnet.manager import Manager

    manager = Manager()

    msg = make_privmsg('.bots')

    manager.load_module_by_name('meta')
    rec_msg(msg)
    assert len(msg_l.msgs) == 1

    manager.unload_module_by_name('meta')
    rec_msg(msg)
    assert len(msg_l.msgs) == 1

    manager.load_module_by_name('meta')
    rec_msg(msg)
    assert len(msg_l.msgs) == 2


def test_reload_meta_with_admin(cl, msg_l, make_privmsg, rec_msg):
    """Load, send, unload, send, load, send."""
    from botnet.manager import Manager
    from modules.builtin.test_admin import admin_make_message, data4, send_data

    msg = make_privmsg('.bots')

    manager = Manager()
    manager.config = make_admin_config()
    manager.load_module_by_name('admin')

    # load
    amsg = admin_make_message('nick4', ':.module_load meta')
    rec_msg(amsg)
    send_data(data4)
    assert len(msg_l.msgs) == 2 # WHOIS, loaded module

    # send
    rec_msg(msg)
    assert len(msg_l.msgs) == 3 # response

    # unload
    amsg = admin_make_message('nick4', ':.module_unload meta')
    rec_msg(amsg)
    assert len(msg_l.msgs) == 4 # unloaded module

    # send
    rec_msg(msg)
    assert len(msg_l.msgs) == 4 # should not respond 

    # load
    amsg = admin_make_message('nick4', ':.module_load meta')
    rec_msg(amsg)
    assert len(msg_l.msgs) == 5 # loaded module

    # send
    rec_msg(msg)
    assert len(msg_l.msgs) == 6 # response


def test_reload_tv(cl, msg_l, make_privmsg, rec_msg):
    """Load, send, unload, send, load, send."""
    from botnet.manager import Manager

    manager = Manager()

    msg = make_privmsg('.next_episode a')

    manager.load_module_by_name('tv')
    rec_msg(msg)
    assert len(msg_l.msgs) == 1

    manager.unload_module_by_name('tv')
    # (always?) fixed by adding those lines right here:
    #import gc
    #gc.collect()
    # this does not fix the issue during real usage
    rec_msg(msg)
    assert len(msg_l.msgs) == 1

    manager.load_module_by_name('tv')
    rec_msg(msg)
    assert len(msg_l.msgs) == 2


def test_reload_tv_with_admin(cl, msg_l, make_privmsg, rec_msg):
    """Load, send, unload, send, load, send."""
    from botnet.manager import Manager
    from modules.builtin.test_admin import admin_make_message, data4, send_data

    msg = make_privmsg('.next_episode a')

    manager = Manager()
    manager.config = make_admin_config()
    manager.load_module_by_name('admin')

    # load
    amsg = admin_make_message('nick4', ':.module_load tv')
    rec_msg(amsg)
    send_data(data4)
    assert len(msg_l.msgs) == 2 # WHOIS, loaded module

    # send
    rec_msg(msg)
    assert len(msg_l.msgs) == 3 # response

    # unload
    amsg = admin_make_message('nick4', ':.module_unload tv')
    rec_msg(amsg)
    assert len(msg_l.msgs) == 4 # unloaded module

    # (always?) fixed by adding those lines right here:
    #import gc
    #gc.collect()
    # this does not fix the issue during real usage

    # send
    rec_msg(msg)
    assert len(msg_l.msgs) == 4 # should not respond 

    # load
    amsg = admin_make_message('nick4', ':.module_load tv')
    rec_msg(amsg)
    assert len(msg_l.msgs) == 5 # loaded module

    # send
    rec_msg(msg)
    assert len(msg_l.msgs) == 6 # response
