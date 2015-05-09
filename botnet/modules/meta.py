from . import BaseResponder, parse_command
from ..signals import  _request_list_commands, _list_commands


class Meta(BaseResponder):
    """Displays basic info about this bot."""

    ignore_help = False

    def __init__(self, config):
        super(Meta, self).__init__(config)
        _list_commands.connect(self.on_list_commands)

    def command_bots(self, msg):
        """Makes the bot identify itself."""
        self.respond(msg, 'Botnet https://github.com/boreq/botnet')

    def command_git(self, msg):
        """Alias for `bots`."""
        self.command_bots(msg)

    @parse_command([('command_names', '*')])
    def command_help(self, msg, args):
        """Sends a list of commands. If COMMAND is specified sends detailed help
        in a private message.

        Syntax: help [COMMAND ...]
        """
        if len(args.command_names) == 0:
            _request_list_commands.send(self, msg=msg)
        else:
            super(Meta, self).command_help(msg)

    def on_list_commands(self, sender, msg, commands):
        """Sends a list of commands received from the Manager."""
        text = 'Supported commands: %s' % ', '.join(commands)
        self.respond(msg, text)


mod = Meta
