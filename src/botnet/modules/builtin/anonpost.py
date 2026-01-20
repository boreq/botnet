from ...signals import message_out
from ...message import Message
from .. import BaseResponder, command, only_admins
from ..lib import parse_command
from ...helpers import is_channel_name


class Anonpost(BaseResponder):
    """Allows users to post anonymously."""

    config_namespace = 'botnet'
    config_name = 'anonpost'

    @command('anonpost')
    @parse_command([('target', 1), ('message', '+')])
    def command_anonpost(self, msg, auth, args):
        """Send a message to a target channel anonymously.

        Syntax: anonpost TARGET MESSAGE
        """
        target = args.target[0]
        message = 'ANONPOST: ' + ' '.join(args.message)

        if is_channel_name(target):
            self._send(target, message)

    @command('anonpost')
    @only_admins()
    @parse_command([('target', 1), ('message', '+')])
    def admin_command_anonpost(self, msg, auth, args):
        """Send a message to a target user anonymously.

        Syntax: anonpost TARGET MESSAGE
        """
        target = args.target[0]
        message = 'ANONPOST: ' + ' '.join(args.message)

        if not is_channel_name(target):
            self._send(target, message)

    def _send(self, target, message):
        msg = Message(command='PRIVMSG', params=[target, message])
        message_out.send(self, msg=msg)


mod = Anonpost
