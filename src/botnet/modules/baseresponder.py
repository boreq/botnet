from dataclasses import dataclass
from typing import TypeVar

from ..message import IncomingPrivateMessage
from ..message import Message
from ..message import Target
from ..signals import message_out
from .base import AuthContext
from .base import BaseModule
from .decorators import Args
from .decorators import command
from .decorators import parse_command
from .lib import divide_text
from .mixins import ConfigMixin
from .mixins import DataclassInstance
from .mixins import MessageDispatcherMixin

_BREAK_PRIVMSG_EVERY = 400


T = TypeVar('T', bound=DataclassInstance)


@dataclass
class BaseResponderConfig:
    command_prefix: str | None

    def __post_init__(self) -> None:
        if self.command_prefix is not None and len(self.command_prefix) == 0:
            raise ValueError('You may think that an empty command prefix is a good idea and will work, but it is in fact not and will not.')


class BaseResponder(ConfigMixin[T], MessageDispatcherMixin, BaseModule):
    """Inherit from this class to quickly create a module which reacts to users'
    messages.

    Example module config:

        "botnet": {
            "base_responder": {
                "command_prefix": "."
            }
        }

    """

    # Don't send description of the .help command - normally each module which
    # is based on this class would respond to such request and flood a user with
    # messages. This should be set to False only in one module (by default in
    # module meta). Note that this parameter is a terrible workaround. The
    # problem is caused by the fact that modules do not have direct access to
    # each another, so it is not possible to query others modules for commands.
    # Each module has to report them separately, and in effect the same command
    # had to be defined in all modules.
    ignore_help = True

    def get_command_prefix(self) -> str:
        config = self.peek_loaded_config_for_module('botnet', 'base_responder', BaseResponderConfig)
        return config.command_prefix if config.command_prefix else '.'

    def respond(self, msg: IncomingPrivateMessage, text: str, pm: bool = False) -> None:
        """Send a text in response to a message. Text will be automatically
        sent to a proper channel or user.

        msg: Message to which we are responding.
        text: Response text.
        pm: If True response will be a private message.
        """
        # If this is supposed to be sent as a private message or was sent in
        # a private message to the bot respond also in private message.
        if pm or msg.target.is_nick:
            target = Target(msg.sender)
        else:
            target = msg.target
        self.message(target, text)

    def message(self, nick_or_channel: Target, text: str) -> None:
        """Send the text as a message to the provided nick or channel."""
        for part in divide_text(text, _BREAK_PRIVMSG_EVERY):
            response = Message(command='PRIVMSG', params=[str(nick_or_channel), part])
            message_out.send(self, msg=response)

    @command('help')
    @parse_command([('command_names', '+')])
    def command_help(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Sends a list of commands. If COMMAND is specified sends more
        detailed help about a single command.

        Syntax: help [COMMAND ...]
        """
        for name in args['command_names']:
            if self.ignore_help and name == 'help':
                continue

            for help_text in self.get_help_for_command(name, msg, auth):
                self.respond(msg, help_text)
