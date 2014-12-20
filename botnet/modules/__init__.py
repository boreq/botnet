import threading
from ..codes import Code
from ..message import Message
from ..signals import message_in, message_out


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
    """Attempts to find a module class by name. This function looks for a
    Python module named `module_name` located in `botnet.modules`. A found Python
    module is expected to contain a variable called `mod` pointing to an actual
    module class. If the name is prefixed with `botnet_` this function will look
    for an external module class instead.
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
    """Base module which does not run anything in a loop."""

    def __init__(self, config):
        pass


class BaseModule(BaseIdleModule):
    """Base module with a loop used for periodic updates."""

    deltatime = .016

    def __init__(self, *args, **kwargs):
        super(BaseModule, self).__init__(*args, **kwargs)
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        self.stop_event.clear()
        while not self.stop_event.is_set():
            self.update()
            self.stop_event.wait(self.deltatime)

    def update(self):
        """This is executed every time deltatime passes."""
        pass


class BaseResponder(BaseIdleModule):
    """Inherit from this class to quickly create a module which reacts to users'
    messages. Each incomming PRIVMSG is dispatched to the `handle_message`
    method. If a message starts with a command_prefix defined in config it will
    be also sent to a proper handler, for example `handler_help`.

    Example config:

        "base_responder": {
            "command_prefix": "."
        }
    """

    # Prefix for command handlers. For example `command_help` is a handler for
    # messages starting with .help
    handler_prefix = 'command_'

    def __init__(self, *args, **kwargs):
        super(BaseResponder, self).__init__(*args, **kwargs)
        message_in.connect(self.on_message_in)
        self.base_config = args[0]['module_config']['base_responder']
        self._commands = self._get_commands_from_handlers()

    def _get_commands_from_handlers(self):
        """Generates a list of supported commands from defined handlers."""
        commands = []
        for name in dir(self):
            if name.startswith(self.handler_prefix):
                attr = getattr(self, name)
                if hasattr(attr, '__call__'):
                    commands.append(name[len(self.handler_prefix):])
        return commands

    def command_help(self, msg):
        """Handler for the help command."""
        text = 'Module %s, commands: %s' % (self.__class__.__name__, self._commands)
        self.respond(msg, text, pm=True)

    def on_message_in(self, sender, **kwargs):
        """Handler for a message_in signal. Dispatches the message to the 
        handlers.
        """
        if kwargs['msg'].command == 'PRIVMSG':
            # Main handler
            self.handle_message(kwargs['msg'])
            # Command-specific handler
            if self.is_command(kwargs['msg']):
                # First word of the last parameter:
                cmd_name = kwargs['msg'].params[-1].split(' ')[0]
                cmd_name = cmd_name.strip('.')
                handler_name = self.handler_prefix + cmd_name
                func = getattr(self, handler_name, None)
                if func is not None:
                    func(kwargs['msg'])

    def handle_message(self, msg):
        """General handler for called if a message is a PRIVMSG."""
        pass

    def is_command(self, priv_msg, command_name=None):
        """Returns True if the message text starts with a command_name and a
        prefix. If command_name is None this function will simply check if the
        message is prefixed with a command prefix.
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
        if not pm:
            target = priv_msg.params[0]
        else:
            target = priv_msg.nickname
        response = Message(command='PRIVMSG', params=[target, text])
        message_out.send(self, msg=response)
