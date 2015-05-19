from botnet import BaseResponder
from botnet.modules.lib import parse_command


class SimpleModule(BaseResponder):
    """A simple module which implements several simple commands. It utilizes
    the BaseResponder class which automatically dispatches user commands to the
    methods called `command_<command_name>`.
    """

    def command_respond(self, msg):
        """Sends a message 'Responding!'.

        Syntax: respond
        """
        self.respond(msg, 'Responding!')

    def command_hi(self, msg):
        """Sends 'Hello <nick>!', where <nick> is a nick of the sender of
        the message.

        Syntax: hi
        """
        text = 'Hello %s!' % msg.nickname
        self.respond(msg, text)

    @parse_command([('text', '*')])
    def command_say(self, msg, args):
        """Sends the text specified in the command.

        Syntax: say TEXT
        """
        if not args.text:
            self.respond(msg, 'You forgot to tell me what to say %s!' % msg.nickname)
        else:
            text = ' '.join(args.text)
            self.respond(msg, '%s told me to say: %s' % (msg.nickname, text))


mod = SimpleModule
