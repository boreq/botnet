"""
    Since all modules are designed to be standalone and independent, signals are
    the only way modules can communicate with each other or other components
    of the bot.
"""


from blinker import Namespace
import inspect


_signals = Namespace()

# Sent when a message is received
# kwargs: Message msg
message_in = _signals.signal('message-in')

# Sent when a message is confirmed to originate from a bot admin
# (That means that a message originating from an admin will be picked up as a
# message_in signal first and after that as a admin_message_in signal)
# kwargs: Message msg
admin_message_in = _signals.signal('admin-message-in')

# Send this signal to send a messages to the IRC server
# kwargs: Message msg
message_out = _signals.signal('message-out')

# Used to report exceptions
# kwargs: Exception e
on_exception = _signals.signal('on-exception')

# Send this signal to load a module
# kwargs: str name
module_load = _signals.signal('module-load')

# Send this signal to unload a module
# kwargs: str name
module_unload = _signals.signal('module-unload')

# Sent after a module is loaded
# kwargs: type cls
module_loaded = _signals.signal('module-loaded')

# Sent after a module is unloaded
# kwargs: type cls
module_unloaded = _signals.signal('module-unloaded')

# Send this to reload the config
# no kwargs
config_reload = _signals.signal('config-reload')

# Sent after the config is reloaded
# no kwargs
config_reloaded = _signals.signal('config-reloaded')

# Send this to indicate that the config has changed and should be saved
# no kwargs
config_changed = _signals.signal('config-changed')

# Meta module sends this to request `_list_commands` signal
# kwargs: Message msg, bool admin
# msg: message to which the bot should respond with the list of commands
# admin: if True the response signal will contain the admin commands
_request_list_commands = _signals.signal('_request_list_commands')

# Manager sends this in response to `_request_list_commands` signal
# kwargs: Message msg, bool admin, [str,] commands
# msg: message to which the bot should respond with the list of commands
_list_commands = _signals.signal('_list_commands')


def unsubscribe_from_all(module):
    """Unsubscribes a bot module from all signals. Called when a module is
    unloaded. That is necessary because if a module is a part of a reference
    cycle it will not be deleted by refcounting alone and it will stay in the
    memory for a while longer before the garbage collector removes it.
    Unsubscribing is supposed to avoid a situation when an unloaded module is
    still reacting to commands. Another solution to that problem would involve
    calling `gc.collect()` periodically to force the collection, require the
    modules to unsubscribe from signals on their own or require that the modules
    free all circular dependencies when terminating.
    """
    for name, signal in _signals.items():
        for receiver in list(signal.receivers.values()):
            obj = receiver()
            if obj is not None:
                if inspect.ismethod(obj):
                    # find the object to which a method is bound
                    self = None
                    for name, value in inspect.getmembers(obj):
                        if name == '__self__':
                            self = value
                    # if this is a method which belongs to the module
                    if self is not None and self is module:
                        signal.disconnect(obj)


def clear_state():
    """Removes all state from signals. Used in unit tests."""
    for name, signal in _signals.items():
        signal._clear_state()
