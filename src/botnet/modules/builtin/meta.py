from ...signals import _request_list_commands, _list_commands
from ...message import IncomingPrivateMessage, Text
from .. import BaseResponder, AuthContext, command, parse_command, Args
from ...config import Config


class Meta(BaseResponder):
    """Displays basic info about this bot."""

    ignore_help = False
    ibip_repo = 'https://github.com/boreq/botnet'
    ibip_website = 'https://ibip.0x46.net/'

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        _list_commands.connect(self.on_list_commands)

    @command('git')
    def command_git(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
        """Alias for the IBIP identification.

        Syntax: git
        """
        self._respond_with_ibip(msg)

    @command('help')
    @parse_command([('command_names', '*')])
    def command_help(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Sends a list of commands. If COMMAND is specified sends more
        detailed help about a single command.

        Syntax: help [COMMAND ...]
        """
        if len(args['command_names']) == 0:
            _request_list_commands.send(self, msg=msg, auth=auth)
        else:
            super().command_help(msg, auth)

    def on_list_commands(self, sender, msg: IncomingPrivateMessage, auth: AuthContext, commands: list[str]) -> None:
        """Sends a list of commands received from the Manager."""
        text = 'Supported commands: %s' % ', '.join(commands)
        self.respond(msg, text)

    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        if msg.text == Text('.bots'):
            self._respond_with_ibip(msg)

    def _respond_with_ibip(self, msg: IncomingPrivateMessage) -> None:
        """Makes the bot identify itself as defined by The IRC Bot
        Identification Protocol Standard.
        """
        text = 'Reporting in! [Python] {ibip_repo} try {prefix}help ({ibip_website})'.format(
            ibip_repo=self.ibip_repo,
            prefix=self.config_get('command_prefix'),
            ibip_website=self.ibip_website,
        )
        self.respond(msg, text)


mod = Meta
