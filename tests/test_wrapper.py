from botnet.wrappers import ModuleWrapper


class ModuleMock():

    def __init__(self, *args, **kwargs):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def test_wrapper_start():
    m = ModuleMock()
    w = ModuleWrapper(m)
    w.start()
    assert m.started


def test_wrapper_stop():
    m = ModuleMock()
    w = ModuleWrapper(m)
    w.stop()
    assert m.stopped
