import re
from ..helpers import is_channel_name
from ..message import Message
from ..signals import message_out
from .base import BaseModule
from .mixins import ConfigMixin, MessageDispatcherMixin
from .lib import parse_command


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
    config_namespace = None
    config_name = None

    # This is the default config for this class
    base_default_config = {
        "command_prefix": "."
    }

    # Default config for the class which inherits from BaseResponder
    default_config = {}

    def __init__(self, config):
        super(BaseResponder, self).__init__(config)
        self.register_default_config(self.base_default_config)
        self.register_default_config(self.default_config)
        self.register_config('botnet', 'base_responder')
        if self.config_namespace and self.config_name:
            self.register_config(self.config_namespace, self.config_name)

    def _get_commands_from_handlers(self, handler_prefix):
        """Generates a list of supported commands from defined handlers."""
        commands = []
        for name in dir(self):
            if name.startswith(handler_prefix):
                attr = getattr(self, name)
                if hasattr(attr, '__call__'):
                    command_name = name[len(handler_prefix):]
                    if not (self.ignore_help and command_name == 'help'):
                        commands.append(command_name)
        return commands

    def _get_help_for_command(self, handler_prefix, name):
        handler = self._get_command_handler(handler_prefix, name)
        if not handler:
            return None
        # Header
        rw = 'Module %s, help for `%s`: ' % (self.__class__.__name__,
                                             name)
        # Docstring
        help_text = handler.__doc__
        if help_text:
            rw += ' '.join(help_text.splitlines())
        else:
            rw += 'No help available.'

        rw = re.sub(' +', ' ', rw)
        return rw

    def get_command_prefix(self):
        return self.config_get('command_prefix')

    def respond(self, priv_msg, text, pm=False):
        """Send a text in response to a message. Text will be automatically
        sent to a proper channel or user.

        priv_msg: Message object to which we are responding.
        text: Response text.
        pm: If True response will be a private message.
        """
        # If this is supposed to be sent as a private message or was sent in
        # a private message to the bot respond also in private message.
        if pm or not is_channel_name(priv_msg.params[0]):
            target = priv_msg.nickname
        else:
            target = priv_msg.params[0]
        response = Message(command='PRIVMSG', params=[target, text])
        message_out.send(self, msg=response)

    def get_all_commands(self):
        """Should return a list of strings containing all commands supported by
        this module.
        """
        return self._get_commands_from_handlers(self.handler_prefix)

    def get_all_admin_commands(self):
        """Should return a list of strings containing all admin commands
        supported by this module.
        """
        return self._get_commands_from_handlers(self.admin_handler_prefix)

    @parse_command([('command_names', '*')])
    def command_help(self, msg, args):
        """If COMMAND is specified sends detailed help for the commands in a
        private message.

        Syntax: help [COMMAND ...]
        """
        if len(args.command_names) > 0:
            # Display help for a specific command
            for name in args.command_names:
                if self.ignore_help and name == 'help':
                    continue

                # get help
                lines = []
                for prefix in [self.handler_prefix, self.admin_handler_prefix]:
                    text = self._get_help_for_command(prefix, name)
                    if text:
                        lines.append(text)

                # send help
                for line in lines:
                    self.respond(msg, line, pm=True)
