from ...signals import _request_list_commands, _list_commands
from .. import BaseResponder
from ..lib import parse_command


class Meta(BaseResponder):
    """Displays basic info about this bot."""

    ignore_help = False
    ibip_repo = 'https://github.com/boreq/botnet'

    def __init__(self, config):
        super(Meta, self).__init__(config)
        _list_commands.connect(self.on_list_commands)

    def command_git(self, msg):
        """Alias for the IBIP identification.

        Syntax: git
        """
        self.ibip(msg)

    @parse_command([('command_names', '*')])
    def command_help(self, msg, args):
        """Sends a list of commands. If COMMAND is specified sends detailed help
        in a private message.

        Syntax: help [COMMAND ...]
        """
        if len(args.command_names) == 0:
            _request_list_commands.send(self, msg=msg, admin=False)
        else:
            super(Meta, self).command_help(msg)

    @parse_command([('command_names', '*')])
    def admin_command_help(self, msg, args):
        """Sends a list of commands. If COMMAND is specified sends detailed help
        in a private message.

        Syntax: help [COMMAND ...]
        """
        if len(args.command_names) == 0:
            _request_list_commands.send(self, msg=msg, admin=True)
        else:
            super(Meta, self).command_help(msg)

    def ibip(self, msg):
        """Makes the bot identify itself as defined by The IRC Bot
        Identification Protocol Standard.
        """
        text = 'Reporting in! [Python] {ibip_repo} try {prefix}help'.format(
            ibip_repo=self.ibip_repo,
            prefix=self.config_get('command_prefix')
        )
        self.respond(msg, text)

    def on_list_commands(self, sender, msg, admin, commands):
        """Sends a list of commands received from the Manager."""
        if admin:
            text = 'Supported admin commands: %s' % ', '.join(commands)
        else:
            text = 'Supported commands: %s' % ', '.join(commands)
        self.respond(msg, text)

    def handle_privmsg(self, msg):
        # Handle IBIP:
        if self.is_command(msg, 'bots', command_prefix='.'):
            self.ibip(msg)


mod = Meta
