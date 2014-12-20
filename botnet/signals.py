from blinker import Namespace


_signals = Namespace()

# kwargs: Message msg
message_in = _signals.signal('message-in')
# kwargs: Message msg
message_out = _signals.signal('message-out')
