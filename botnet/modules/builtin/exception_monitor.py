import sys
import traceback
from .. import BaseModule
from ..mixins import ConfigMixin
from ...signals import on_exception


class ExceptionMonitor(ConfigMixin, BaseModule):
    """Gathers incoming reports about exceptions and logs them.

    Example module config:

        "botnet": {
            "exception_monitor": {
                "log": true
            }
        }

    """

    default_config = {
        'log': True
    }

    error_text = '{error}\nTraceback:\n{tb}'

    def __init__(self, config):
        super(ExceptionMonitor, self).__init__(config)
        self.register_default_config(self.default_config)
        self.register_config('botnet', 'exception_monitor')
        on_exception.connect(self.on_exception)

    def get_text(self, e):
        tb = ''.join(traceback.format_tb(e.__traceback__))
        return self.error_text.format(error=repr(e), tb=tb)

    def on_exception(self, sender, **kwargs):
        e = kwargs['e']
        text = self.get_text(e)

        if self.config_get('log'):
            self.logger.error(text)


mod = ExceptionMonitor
