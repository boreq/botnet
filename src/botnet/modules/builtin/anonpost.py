from dataclasses import dataclass
from .. import BaseResponder, command, only_admins, AuthContext, parse_command, Args
from ...message import IncomingPrivateMessage, Target


@dataclass()
class AnonpostConfig:
    pass


class Anonpost(BaseResponder[AnonpostConfig]):
    """Allows users to post anonymously."""

    config_namespace = 'botnet'
    config_name = 'anonpost'
    config_class = AnonpostConfig

    @command('anonpost')
    @parse_command([('target', 1), ('message', '+')])
    def command_anonpost_to_channel(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Send a message to a target channel anonymously.

        Syntax: anonpost TARGET MESSAGE
        """
        target = Target.new_from_string(args['target'][0])
        channel = target.channel
        if channel is not None:
            message = 'ANONPOST: ' + ' '.join(args['message'])
            self.message(target, message)

    @command('anonpost')
    @only_admins()
    @parse_command([('target', 1), ('message', '+')])
    def command_anonpost_to_nick(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Send a message to a target user anonymously.

        Syntax: anonpost TARGET MESSAGE
        """
        target = Target.new_from_string(args['target'][0])
        nick = target.nick
        if nick is not None:
            message = 'ANONPOST: ' + ' '.join(args['message'])
            self.message(target, message)


mod = Anonpost
