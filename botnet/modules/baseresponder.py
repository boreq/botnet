import copy
import re
from functools import partial
from ..helpers import is_channel_name
from ..message import Message
from ..signals import message_in, message_out, on_exception
from .base import BaseIdleModule
from .utils import parse_command


def iterate_dict(d, key):
    """Allows to search a dict using a key.which.looks.like.this instead
    of passing complex lambda expressions to functions.
    """
    location = d
    for i, part in enumerate(key.split('.')):
        if isinstance(location, dict):
            location = location[part]
            yield location
        else:
            raise ValueError('''Tried to access a value which is not a dict. '''
                             '''Failed for key "{}"'''.format(key))


class ConfigMixin(object):

    def __init__(self, config):
        super(ConfigMixin, self).__init__(config)
        self.config = config
        self._defaults = []
        self._configs = []

    def _get_config_key(self, config, key):
        return 'module_config.{}.{}.{}'.format(config[0], config[1], key)

    def register_default_config(self, config):
        """Adds a default config. Default configs are queried for requested
        values in a reverse order in which they were registered so the
        first registered default config will be used last if the
        value is missing.
        """
        self._defaults.append(config)

    def register_config(self, namespace, name):
        """Adds a location of the configuration values used by this module."""
        self._configs.append((namespace, name))

    def config_get(self, key):
        """Tries to get the value assigned to `key` from the registered configs.
        Raises KeyError if a key does not exist in the dictionary,
        Raises ValueError if a value in the key other than the last one is not
        a dict.  For example in a key 'a.b.c' only 'c' can be something else like
        string, int, list etc.
        """
        # configs
        for config in reversed(self._configs):
            actual_key = self._get_config_key(config, key)
            try:
                return next(reversed(list(iterate_dict(self.config, actual_key))))
            except KeyError:
                continue

        # defaults
        for config in reversed(self._defaults):
            try:
                return next(reversed(list(iterate_dict(config, key))))
            except KeyError:
                continue

        raise KeyError


    def config_set(self, key, value):
        actual_key = self._get_config_key(self._configs[-1], key)

        # walk
        location = self.config
        parts = actual_key.split('.')
        for i, part in enumerate(parts[:-1]):
            if isinstance(location, dict):
                if not part in location:
                    location[part] = {}
                location = location[part]
            else:
                raise ValueError('''Tried to change a value which is not a dict. '''
                                 '''Failed for key "{}"'''.format(key))
        location[parts[-1]] = value
        return True

    def config_append(self, key, value):
        try:
            self.config_get(key).append(value)
        except AttributeError as e:
            raise AttributeError('Value for a key "{}" is not a list'.format(key)) from e
        return True


class BaseResponder(ConfigMixin, BaseIdleModule):
    """Inherit from this class to quickly create a module which reacts to users'
    messages. Each incomming PRIVMSG is dispatched to the `handle_privmsg` method
    and all incoming messages are dispatched to `handle_msg` method. If a message
    starts with a command_prefix defined in config it will be also sent to
    a proper handler, for example `command_help`.

    Example config:

        "base_responder": {
            "command_prefix": "."
        }
    """

    # Prefix for command handlers. For example `command_help` is a handler for
    # messages starting with .help
    handler_prefix = 'command_'

    # Don't send description of the .help command - normally each module which
    # is based on this class would respond to such request and flood a user with
    # messages. This should be set to False only in one module (by default in
    # module meta). Note that this parameter is a terrible workaround. The
    # problem is caused by the fact that modules do not have direct access to
    # each another, so it is not possible to query others modules for commands.
    # Each module has to report them separately, and in effect the same command
    # had to be defined in all modules.
    ignore_help = True

    # A module is expected to store the config in
    # config['module_config'][config_namespace][config_name]
    config_namespace = None
    config_name = None

    # This is the default config for this class
    base_default_config = {
        "command_prefix": "."
    }

    # Default config for the class which inherits from BaseResponder
    default_config = {}

    def __init__(self, config):
        super(BaseResponder, self).__init__(config)
        self._commands = self._get_commands_from_handlers()
        message_in.connect(self.on_message_in)

        self.register_default_config(self.base_default_config)
        self.register_default_config(self.default_config)
        self.register_config('botnet', 'base_responder')
        if self.config_namespace and self.config_name:
            self.register_config(self.config_namespace, self.config_name)

    def _get_commands_from_handlers(self):
        """Generates a list of supported commands from defined handlers."""
        commands = []
        for name in dir(self):
            if name.startswith(self.handler_prefix):
                attr = getattr(self, name)
                if hasattr(attr, '__call__'):
                    command_name = name[len(self.handler_prefix):]
                    if not (self.ignore_help and command_name == 'help'):
                        commands.append(command_name)
        return commands

    def _dispatch_message(self, msg):
        # Main handler
        self.handle_msg(msg)
        if msg.command == 'PRIVMSG':
            # PRIVMSG handler
            self.handle_privmsg(msg)
            # Command-specific handler
            if self.is_command(msg):
                # First word of the last parameter:
                cmd_name = msg.params[-1].split(' ')[0]
                cmd_name = cmd_name.strip(self.config_get('command_prefix'))
                func = self._get_command_handler(cmd_name)
                if func is not None:
                    func(msg)

    def _get_command_handler(self, cmd_name):
        """Returns a handler for a command."""
        handler_name = self.handler_prefix + cmd_name
        return getattr(self, handler_name, None)

    def on_message_in(self, sender, msg):
        """Handler for a message_in signal. Dispatches the message to the
        per-command handlers and the main handler.
        """
        try:
            self._dispatch_message(msg)
        except Exception as e:
            on_exception.send(self, e=e)
            raise

    def is_command(self, priv_msg, command_name=None, command_prefix=None):
        """Returns True if the message text starts with a prefixed command_name.
        If command_name is None this function will simply check if the message
        is prefixed with a command prefix. By default the command prefix
        defined in the config is used but you can ovverida it by passing the
        command_prefox parameter.
        """
        if command_prefix is None:
            cmd = self.config_get('command_prefix')
        else:
            cmd = command_prefix

        if command_name:
            cmd += command_name
            return priv_msg.params[-1].split()[0] == cmd
        else:
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
        if pm or not is_channel_name(priv_msg.params[0]):
            target = priv_msg.nickname
        else:
            target = priv_msg.params[0]
        response = Message(command='PRIVMSG', params=[target, text])
        message_out.send(self, msg=response)

    def get_all_commands(self):
        """Should return a list of strings containing all commands supported by
        this module.
        """
        return self._commands

    @parse_command([('command_names', '*')])
    def command_help(self, msg, args):
        """If COMMAND is specified sends detailed help for the commands in a
        private message.

        Syntax: help [COMMAND ...]
        """
        if len(args.command_names) > 0:
            # Display help for a specific command
            for name in args.command_names:
                if self.ignore_help and name == 'help':
                    continue
                lines = []
                handler = self._get_command_handler(name)
                if handler:
                    # Header
                    res = 'Module %s, help for `%s`: ' % (self.__class__.__name__,
                                                          name)
                    # Docstring
                    help_text = handler.__doc__
                    if help_text:
                        res += ' '.join(help_text.splitlines())
                    else:
                        res += 'No help available.'

                    res = re.sub(' +', ' ', res)
                    lines.append(res)

                for line in lines:
                    self.respond(msg, line, pm=True)

    def handle_msg(self, msg):
        """Handler called when a message is received."""
        pass

    def handle_privmsg(self, msg):
        """Handler called when a message with a PRIVMSG command is received."""
        pass
