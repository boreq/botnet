import textwrap
from ..helpers import is_channel_name
from ..message import Message, IncomingPrivateMessage
from ..signals import message_out
from .base import BaseModule, AuthContext
from .decorators import command
from .mixins import ConfigMixin, MessageDispatcherMixin
from .lib import parse_command, Args


_BREAK_PRIVMSG_EVERY = 400


class BaseResponder(ConfigMixin, MessageDispatcherMixin, BaseModule):
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

    # A module is expected to store the config in
    # config['module_config'][config_namespace][config_name]
    config_namespace: str | None = None
    config_name: str | None = None

    # This is the default config for this class
    base_default_config = {
        "command_prefix": "."
    }

    # Default config for the class which inherits from BaseResponder
    default_config: dict = {}

    def __init__(self, config):
        super().__init__(config)
        self.register_default_config(self.base_default_config)
        self.register_default_config(self.default_config)
        self.register_config('botnet', 'base_responder')
        if self.config_namespace and self.config_name:
            self.register_config(self.config_namespace, self.config_name)

    def get_command_prefix(self) -> str:
        return self.config_get('command_prefix')

    def respond(self, msg: IncomingPrivateMessage, text: str, pm: bool = False) -> None:
        """Send a text in response to a message. Text will be automatically
        sent to a proper channel or user.

        priv_msg: Message object to which we are responding.
        text: Response text.
        pm: If True response will be a private message.
        """
        # If this is supposed to be sent as a private message or was sent in
        # a private message to the bot respond also in private message.
        if pm or not is_channel_name(msg.target):
            target = msg.sender
        else:
            target = msg.target
        self.message(target, text)

    def message(self, nick_or_channel: str, text: str) -> None:
        """Send the text as a message to the provided nick or channel."""
        for part in textwrap.wrap(text, width=_BREAK_PRIVMSG_EVERY):
            response = Message(command='PRIVMSG', params=[nick_or_channel, part])
            message_out.send(self, msg=response)

    @command('help')
    @parse_command([('command_names', '+')])
    def command_help(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Sends a list of commands. If COMMAND is specified sends more
        detailed help about a single command.

        Syntax: help [COMMAND ...]
        """
        for name in args.command_names:
            if self.ignore_help and name == 'help':
                continue

            for help_text in self.get_help_for_command(name, msg, auth):
                self.respond(msg, help_text)
