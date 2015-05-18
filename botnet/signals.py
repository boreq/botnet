"""
    Since all modules are designed to be standalone and independent, signals are
    the only way modules can communicate with each other or other components
    of the bot.
"""


from blinker import Namespace


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

# Meta module sends this to request `_list_commands` signal
# kwargs: Message msg
# msg: message to which the bot should respond with the list of commands
_request_list_commands = _signals.signal('_request_list_commands')

# Manager sends this in response to `_request_list_commands` signal
# kwargs: Message msg, [str,] commands
# msg: message to which the bot should respond with the list of commands
_list_commands = _signals.signal('_list_commands')
