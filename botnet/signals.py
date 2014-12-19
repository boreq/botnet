from blinker import Namespace


_signals = Namespace()
message_in = _signals.signal('message-in')
message_out = _signals.signal('message-out')
