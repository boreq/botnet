from botnet.config import Config
from botnet.modules import BaseModule
from botnet.wrappers import ModuleWrapper


class ModuleMock(BaseModule):

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


def test_wrapper_start() -> None:
    m = ModuleMock(Config({}))
    w = ModuleWrapper(m)
    w.start()
    assert m.started


def test_wrapper_stop() -> None:
    m = ModuleMock(Config({}))
    w = ModuleWrapper(m)
    w.stop()
    assert m.stopped
