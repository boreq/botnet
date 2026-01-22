from .. import BaseResponder, command, only_admins, AuthContext, parse_command, Args
from ...message import IncomingPrivateMessage
from ...helpers import is_channel_name


class Anonpost(BaseResponder):
    """Allows users to post anonymously."""

    config_namespace = 'botnet'
    config_name = 'anonpost'

    @command('anonpost')
    @parse_command([('target', 1), ('message', '+')])
    def command_anonpost(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Send a message to a target channel anonymously.

        Syntax: anonpost TARGET MESSAGE
        """
        target = args['target'][0]
        message = 'ANONPOST: ' + ' '.join(args['message'])

        if is_channel_name(target):
            self.message(target, message)

    @command('anonpost')
    @only_admins()
    @parse_command([('target', 1), ('message', '+')])
    def admin_command_anonpost(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Send a message to a target user anonymously.

        Syntax: anonpost TARGET MESSAGE
        """
        target = args['target'][0]
        message = 'ANONPOST: ' + ' '.join(args['message'])

        if not is_channel_name(target):
            self.message(target, message)


mod = Anonpost
