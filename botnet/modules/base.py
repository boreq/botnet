import threading
from ..signals import on_exception
from ..logging import get_logger


class BaseIdleModule(object):
    """Base class for all modules."""

    def __init__(self, config):
        self._logger = None

    def get_all_commands(self):
        """Should return a list of strings containing all commands supported by
        this module. Used to generate a help message.
        """
        return []

    @property
    def logger(self):
        if not self._logger:
            self._logger = get_logger(self)
        return self._logger


class BaseModule(BaseIdleModule):
    """Base module with a loop used for periodic updates."""

    deltatime = .016

    def __init__(self, config):
        super(BaseModule, self).__init__(config)
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        self.stop_event.clear()
        while not self.stop_event.is_set():
            try:
                self.update()
            except Exception as e:
                on_exception.send(self, e=e)
            self.stop_event.wait(self.deltatime)

    def update(self):
        """This is executed every time deltatime passes."""
        pass
