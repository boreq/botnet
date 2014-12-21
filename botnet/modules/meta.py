from . import BaseResponder


class Meta(BaseResponder):
    """Displays basic info about this bot."""

    def command_bots(self, msg):
        """Makes the bot identify itself."""
        self.respond(msg, 'Botnet https://github.com/boreq/botnet')

    def command_git(self, msg):
        """Alias for `bots`."""
        self.command_bots(msg)


mod = Meta
