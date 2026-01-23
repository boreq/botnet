from .. import signals
from ..logging import get_logger, Logger
from ..message import IncomingPrivateMessage
from dataclasses import dataclass


@dataclass
class AuthContext:
    uuid: str | None
    groups: list[str]


class BaseModule:
    """Base class for all modules."""

    def __init__(self, config) -> None:
        self._logger: Logger | None = None

    def get_all_commands(self, msg: IncomingPrivateMessage, auth: AuthContext) -> set[str]:
        """Should return a set of strings containing all commands supported by
        this module. Used to generate a help message.

        msg: message in which the user requested a list of commands.
        auth: the auth context associated with the message.
        """
        return set()

    def start(self) -> None:
        """Called when the module is loaded."""
        pass

    def stop(self) -> None:
        """Called when the module is unloaded. Here you can for example stop the
        execution of all threads the module has created and wait for them to
        finish before returning.
        """
        signals.unsubscribe_from_all(self)

    @property
    def logger(self) -> Logger:
        """Modules can use the logger instance returned by this property."""
        if not self._logger:
            self._logger = get_logger(self)
        return self._logger
