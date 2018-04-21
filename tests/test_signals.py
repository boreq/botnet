from botnet.config import Config
from botnet.modules import BaseResponder
from botnet import signals


def test_unsubscribe_from_all(cl):
    r = BaseResponder(Config())

    assert signals.message_in.receivers
    assert signals.admin_message_in.receivers

    signals.unsubscribe_from_all(r)

    assert not signals.message_in.receivers
    assert not signals.admin_message_in.receivers


def test_clear_state_doesnt_throw():
    signals.clear_state() 
