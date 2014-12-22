from blinker import Namespace


_signals = Namespace()

# Sent when a message is received
# kwargs: Message msg
message_in = _signals.signal('message-in')

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
