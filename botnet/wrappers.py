from .logging import get_logger
from .modules import get_ident_string


class ModuleWrapper(object):
    """Wraps a module. It is used to hold a reference to a loaded module in the
    Manager.
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
