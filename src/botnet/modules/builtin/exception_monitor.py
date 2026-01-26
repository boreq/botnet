import traceback
from typing import Any
from .. import BaseModule
from ...signals import on_exception
from ...config import Config


class ExceptionMonitor(BaseModule):
    """Gathers incoming reports about exceptions and logs them."""

    error_text = '{text}, {error}\nTraceback:\n{tb}'

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        on_exception.connect(self.on_exception)

    def on_exception(self, sender: object, **kwargs: Any) -> None:
        e = kwargs['e']
        text = self._get_text(e)
        self.logger.error(text)

    def _get_text(self, e: Exception) -> str:
        tb = ''.join(traceback.format_tb(e.__traceback__))
        return self.error_text.format(text=str(e), error=repr(e), tb=tb)


mod = ExceptionMonitor
