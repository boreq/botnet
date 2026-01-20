from ...signals import _request_list_commands, _list_commands
from ...message import Message
from .. import BaseResponder, AuthContext, command
from ..lib import parse_command


class Meta(BaseResponder):
    """Displays basic info about this bot."""

    ignore_help = False
    ibip_repo = 'https://github.com/boreq/botnet'

    def __init__(self, config):
        super().__init__(config)
        _list_commands.connect(self.on_list_commands)

    @command('git')
    def command_git(self, msg: Message, auth: AuthContext) -> None:
        """Alias for the IBIP identification.

        Syntax: git
        """
        self.ibip(msg)

    @command('help')
    @parse_command([('command_names', '*')])
    def command_help(self, msg: Message, auth: AuthContext, args) -> None:
        """Sends a list of commands. If COMMAND is specified sends more
        detailed help about a single command.

        Syntax: help [COMMAND ...]
        """
        if len(args.command_names) == 0:
            _request_list_commands.send(self, msg=msg, auth=auth)
        else:
            super().command_help(msg, auth)

    def ibip(self, msg: Message) -> None:
        """Makes the bot identify itself as defined by The IRC Bot
        Identification Protocol Standard.
        """
        text = 'Reporting in! [Python] {ibip_repo} try {prefix}help'.format(
            ibip_repo=self.ibip_repo,
            prefix=self.config_get('command_prefix')
        )
        self.respond(msg, text)

    def on_list_commands(self, sender, msg: Message, auth: AuthContext, commands: list[str]) -> None:
        """Sends a list of commands received from the Manager."""
        text = 'Supported commands: %s' % ', '.join(commands)
        self.respond(msg, text)

    def handle_privmsg(self, msg):
        if msg.params[1] == '.bots':
            self.ibip(msg)


mod = Meta
