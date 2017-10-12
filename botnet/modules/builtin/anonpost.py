from ...signals import message_out
from ...message import Message
from .. import BaseResponder
from ..lib import parse_command
from ...helpers import is_channel_name


class Anonpost(BaseResponder):
    """Allows users to post anonymously."""

    config_namespace = 'botnet'
    config_name = 'anonpost'

    @parse_command([('target', 1), ('message', '+')], launch_invalid=False)
    def command_anonpost(self, msg, args):
        """Send a message to a target channel anonymously.

        Syntax: anonpost TARGET MESSAGE
        """
        target = args.target[0]
        message = 'ANONPOST: ' + ' '.join(args.message)

        if is_channel_name(target):
            msg = Message(command='PRIVMSG', params=[target, message])
            message_out.send(self, msg=msg)

    @parse_command([('target', 1), ('message', '+')], launch_invalid=False)
    def admin_command_anonpost(self, msg, args):
        """Send a message to a target channel anonymously.

        Syntax: anonpost TARGET MESSAGE
        """
        target = args.target[0]
        message = 'ANONPOST: ' + ' '.join(args.message)

        if not is_channel_name(target):
            msg = Message(command='PRIVMSG', params=[target, message])
            message_out.send(self, msg=msg)


mod = Anonpost
