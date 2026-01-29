from dataclasses import dataclass

from botnet import signals
from botnet.config import Config
from botnet.modules import BaseResponder


def test_unsubscribe_from_all(clear_signal_state: None) -> None:
    @dataclass()
    class ConfigClass:
        pass

    r: BaseResponder[ConfigClass] = BaseResponder(Config())

    assert signals.message_in.receivers
    assert signals.auth_message_in.receivers

    signals.unsubscribe_from_all(r)

    assert not signals.message_in.receivers
    assert not signals.auth_message_in.receivers


def test_clear_state_doesnt_throw() -> None:
    signals.clear_state()
