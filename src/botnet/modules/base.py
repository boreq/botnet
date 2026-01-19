from .. import signals
from ..logging import get_logger
from dataclasses import dataclass


@dataclass
class AuthContext:
    uuid: str
    groups: list[str]


class BaseModule(object):
    """Base class for all modules."""

    def __init__(self, config):
        self._logger = None

    def get_all_commands(self, msg_target: str, auth: AuthContext) -> list[str]:
        """Should return a list of strings containing all commands supported by
        this module. Used to generate a help message.

        msg_target: target of the PRIVMSG requesting help e.g. '#channel' or 'nick'.
        auth: the auth context for the user which requested help.
        """
        return []

    def start(self):
        """Called when the module is loaded."""
        pass

    def stop(self):
        """Called when the module is unloaded. Here you can for example stop the
        execution of all threads the module has created and wait for them to
        finish before returning.
        """
        signals.unsubscribe_from_all(self)

    @property
    def logger(self):
        """Modules can use the logger instance returned by this property."""
        if not self._logger:
            self._logger = get_logger(self)
        return self._logger
