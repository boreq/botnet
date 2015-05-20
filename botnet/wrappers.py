import threading
from .modules import BaseModule, get_ident_string
from .logging import get_logger


class ModuleWrapper(object):
    """Wraps a module. If a module inherits from BaseModule it runs that
    module's run method in a separate thread.
    """

    def __init__(self, module):
        super(ModuleWrapper, self).__init__()
        self.module = module
        self.name = get_ident_string(module.__class__)
        self.logger = get_logger(str(self))

    def __repr__(self):
        return '%s: %s' % (self.__class__.__name__, self.module)

    def start(self):
        self.logger.debug('Start')
        self.module.start()

    def stop(self):
        self.logger.debug('Stop')
        self.module.stop()
