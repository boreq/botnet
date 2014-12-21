import threading
from ..codes import Code
from ..helpers import is_channel_name
from ..logging import get_logger
from ..message import Message
from ..signals import message_in, message_out, on_exception


def import_by_name(name):
    """Imports an object from a module. For example if passed name is
    `example.module.thing` this function will return an object called `thing`
    located in `example.module`. This behaviour is similar to normal import
    statement `from example.module import thing`.
    """
    name = name.split('.')
    obj = name[-1]
    module = '.'.join(name[:-1])
    return getattr(__import__(name=module, fromlist=[obj]), obj)


def get_module_class(module_name):
    """Attempts to find a bot module by name. This function looks for a
    Python module named `module_name` located in `botnet.modules`. A found Python
    module is expected to contain a variable called `mod` pointing to an actual
    module class. If the name is prefixed with `botnet_` this function will look
    for an external module instead.
    """
    if not module_name.startswith('botnet_'):
        import_name = 'botnet.modules.%s.mod' % module_name
    else:
        import_name = '%s.mod' % module_name

    try:
        return import_by_name(import_name)
    except ImportError as e:
        return None


class BaseIdleModule(object):
    """Base class for all modules."""

    def __init__(self, config):
        self._logger = None

    @property
    def logger(self):
        if not self._logger:
            self._logger = get_logger(self)
        return self._logger


class BaseModule(BaseIdleModule):
    """Base module with a loop used for periodic updates."""

    deltatime = .016

    def __init__(self, config):
        super(BaseModule, self).__init__(config)
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        self.stop_event.clear()
        while not self.stop_event.is_set():
            try:
                self.update()
            except Exception as e:
                on_exception.send(self, e=e)
            self.stop_event.wait(self.deltatime)

    def update(self):
        """This is executed every time deltatime passes."""
        pass


class BaseResponder(BaseIdleModule):
    """Inherit from this class to quickly create a module which reacts to users'
    messages. Each incomming PRIVMSG is dispatched to the `handle_message`
    method. If a message starts with a command_prefix defined in config it will
    be also sent to a proper handler, for example `command_help`.

    Example config:

        "base_responder": {
            "command_prefix": "."
        }
    """

    # Prefix for command handlers. For example `command_help` is a handler for
    # messages starting with .help
    handler_prefix = 'command_'

    def __init__(self, config):
        super(BaseResponder, self).__init__(config)
        self.base_config = config.get_for_module('base_responder')
        self._commands = self._get_commands_from_handlers()
        message_in.connect(self.on_message_in)

    def _get_commands_from_handlers(self):
        """Generates a list of supported commands from defined handlers."""
        commands = []
        for name in dir(self):
            if name.startswith(self.handler_prefix):
                attr = getattr(self, name)
                if hasattr(attr, '__call__'):
                    commands.append(name[len(self.handler_prefix):])
        return commands

    def _dispatch_message(self, msg):
        if msg.command == 'PRIVMSG':
            # Main handler
            self.handle_message(msg)
            # Command-specific handler
            if self.is_command(msg):
                # First word of the last parameter:
                cmd_name = msg.params[-1].split(' ')[0]
                cmd_name = cmd_name.strip('.')
                func = self._get_command_handler(cmd_name)
                if func is not None:
                    func(msg)

    def _get_command_handler(self, cmd_name):
        """Returns a handler for a command."""
        handler_name = self.handler_prefix + cmd_name
        return getattr(self, handler_name, None)

    def on_message_in(self, sender, **kwargs):
        """Handler for a message_in signal. Dispatches the message to the
        per-command handlers and the main handler.
        """
        try:
            self._dispatch_message(kwargs['msg'])
        except Exception as e:
            on_exception.send(self, e=e)

    def is_command(self, priv_msg, command_name=None):
        """Returns True if the message text starts with a prefixed command_name.
        If command_name is None this function will simply check if the message
        is prefixed with a command prefix.
        """
        cmd = self.base_config['command_prefix']
        if command_name:
            cmd += command_name
        return priv_msg.params[-1].startswith(cmd)

    def respond(self, priv_msg, text, pm=False):
        """Send a text in response to a message. Text will be automatically
        sent to a proper channel or user.

        priv_msg: Message object to which we are responding.
        text: Response text.
        pm: If True response will be a private message.
        """
        # If this is supposed to be sent as a private message or was sent in
        # a private message to the bot respond also in private message.
        self.logger.debug(priv_msg.params[0][0])
        if pm or not is_channel_name(priv_msg.params[0]):
            target = priv_msg.nickname
        else:
            target = priv_msg.params[0]
        response = Message(command='PRIVMSG', params=[target, text])
        message_out.send(self, msg=response)

    def command_help(self, msg):
        """Sends a list of commands in a private message. If COMMAND is
        specified sends help for a single command.

        help [COMMAND]
        """
        text = 'Module %s, ' % self.__class__.__name__
        msg_parts = msg.params[-1].split(' ')
        if len(msg_parts) > 1:
            # Display help for specific command
            for name in msg_parts[1:]:
                handler = self._get_command_handler(name)
                if handler:
                    res = text + 'help for %s:' % name
                    self.respond(msg, res, pm=True)
                    help_text = handler.__doc__
                    if help_text:
                        for line in help_text.splitlines():
                            self.respond(msg, '    ' + line.strip(), pm=True)
                    else:
                        self.respond(msg, '    No help available.', pm=True)
        else:
            # Display all commands
            res = text + 'commands: %s' % self._commands
            self.respond(msg, res, pm=True)

    def handle_message(self, msg):
        """Main handler called if a received command is a PRIVMSG."""
        pass
