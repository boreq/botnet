from . import BaseResponder


class Meta(BaseResponder):

    def command_bots(self, msg):
        self.respond(msg, 'Botnet https://github.com/boreq/botnet')

    def command_git(self, msg):
        self.command_bots(msg)


mod = Meta
