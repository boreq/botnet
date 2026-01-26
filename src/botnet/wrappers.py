from .logging import Logger
from .logging import get_logger
from .modules import BaseModule
from .modules.utils import get_ident_string


class ModuleWrapper:
    """Wraps a module. It is used to hold a reference to a loaded module in the
    Manager.
    """

    module: BaseModule
    name: str
    logger: Logger

    def __init__(self, module: BaseModule) -> None:
        self.module = module
        self.name = get_ident_string(module.__class__)
        self.logger = get_logger(str(self))

    def __repr__(self) -> str:
        return '%s: %s' % (self.__class__.__name__, self.module)

    def start(self) -> None:
        self.logger.debug('Start')
        self.module.start()

    def stop(self) -> None:
        self.logger.debug('Stop')
        self.module.stop()
