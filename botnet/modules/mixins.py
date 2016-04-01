from ..signals import admin_message_in, message_in, on_exception, config_changed


_senti = object()


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
    """Adds various config related methods to a module. Allows the user to
    access config keys by passing a string delimited by dots.

        self.register_config('my_namespace', 'common')
        self.register_config('my_namespace', 'my_module')
        self.config_set('one.two.three', 'value')
        self.config_get('one.two.three')
    """

    def __init__(self, config):
        super(ConfigMixin, self).__init__(config)
        # actual Config object
        self.config = config
        # list of dicts with default configuration values
        self._config_defaults = []
        # list of tuples (namespace, name)
        self._config_locations = []

    def _get_config_key(self, config, key):
        return 'module_config.{}.{}.{}'.format(config[0], config[1], key)

    def register_default_config(self, config):
        """Adds a default config. Default configs are queried for requested
        values in a reverse order in which they were registered in case a value
        is missing from the actual config.
        """
        self._config_defaults.append(config)

    def register_config(self, namespace, name):
        """Adds a location of the configuration values used by this module
        in the config.
        """
        self._config_locations.append((namespace, name))

    def config_get(self, key, default=_senti, auto=_senti):
        """Tries to get the value assigned to `key` from the registered configs.
        Raises KeyError if a key does not exist in the dictionary,
        Raises ValueError if a value which a key tries to subscript is not a dict.

        key: key in the following format: 'one.two.three'
        default: returns this value instead of rising a KeyError if a key is not
                 in the config.
        auto: key will be set in to that value if it is not present in the
              config. And the new value will be returned. Takes precedence over
              default so using those two options together is pointless.
        """
        # configs
        with self.config.lock:
            for config in reversed(self._config_locations):
                actual_key = self._get_config_key(config, key)
                try:
                    return next(reversed(list(iterate_dict(self.config, actual_key))))
                except KeyError:
                    continue

        # defaults
        for config in reversed(self._config_defaults):
            try:
                return next(reversed(list(iterate_dict(config, key))))
            except KeyError:
                continue

        if not auto is _senti:
            self.config_set(key, auto)
            return self.config_get(key)

        if not default is _senti:
            return default

        raise KeyError

    def config_set(self, key, value):
        """Sets a value in the last registered location in the config."""
        if not self._config_locations:
            raise ValueError('No config locations. Call register_config first.')

        actual_key = self._get_config_key(self._config_locations[-1], key)

        # walk
        with self.config.lock:
            location = self.config
            parts = actual_key.split('.')
            for i, part in enumerate(parts[:-1]):
                if isinstance(location, dict):
                    if not part in location:
                        location[part] = {}
                    location = location[part]
                else:
                    raise ValueError("""Tried to change a value which is not a dict. """
                                     """Failed for key '{}'""".format(key))
            location[parts[-1]] = value
        # indicate that the config was modified
        config_changed.send(self)
        return True

    def config_append(self, key, value):
        """Alias for
            self.config_get(key, auto=[]).append(value)
        """
        try:
            self.config_get(key, auto=[]).append(value)
            config_changed.send(self)
        except AttributeError as e:
            raise AttributeError('Value for a key "{}" is not a list'.format(key)) from e
        return True


class BaseMessageDispatcherMixin(object):

    def get_command_name(self, priv_msg):
        """Extracts the used command name from a PRIVMSG message."""
        # Extract the first word the last message parameter:
        cmd_name = priv_msg.params[-1].split(' ')[0]
        # Remove the command prefix
        cmd_name = cmd_name.strip(self.get_command_prefix())
        return cmd_name

    def _get_command_handler(self, handler_prefix, cmd_name):
        """Returns a handler for a command."""
        handler_name = handler_prefix + cmd_name
        return getattr(self, handler_name, None)

    def get_command_prefix(self):
        """This method should return the command prefix."""
        raise NotImplementedError

    def is_command(self, priv_msg, command_name=None, command_prefix=None):
        """Returns True if the message text starts with a `command_name`
        prefixed with `command_prefix`.
        If `command_name` is None this function will simply check if the message
        is prefixed with a command prefix. By default the command prefix
        defined in the config is used but you can ovverida it by passing the
        `command_prefix` parameter.
        """
        if command_prefix is None:
            command_prefix = self.get_command_prefix()

        if command_name:
            cmd = command_prefix + command_name
            spl = priv_msg.params[-1].split()
            if len(spl) > 0:
                return spl[0] == cmd
            else:
                return False
        else:
            return priv_msg.params[-1].startswith(command_prefix)


class StandardMessageDispatcherMixin(BaseMessageDispatcherMixin):
    """Dispatches all messages received via `message_in` signal to the proper
    methods.

    When a message is received via the `message_in` signal:
        Each incomming PRIVMSG is dispatched to the `handle_privmsg` method
        and all incoming messages are dispatched to `handle_msg` method. If a
        message starts with a command_prefix defined in the config it will be
        also sent to a proper handler, for example `command_help`.
    """

    # Prefix for command handlers. For example a method `command_help` would be
    # a handler for messages starting with .help
    handler_prefix = 'command_'

    def __init__(self, config):
        super(StandardMessageDispatcherMixin, self).__init__(config)
        message_in.connect(self.on_message_in)

    def dispatch_message(self, msg):
        """Dispatches a message to all handlers."""
        # Main handler
        self.handle_msg(msg)
        if msg.command == 'PRIVMSG':
            # PRIVMSG handler
            self.handle_privmsg(msg)
            # Command-specific handler
            if self.is_command(msg):
                cmd_name = self.get_command_name(msg)
                func = self._get_command_handler(self.handler_prefix, cmd_name)
                if func is not None:
                    func(msg)

    def on_message_in(self, sender, msg):
        """Handler for a message_in signal. Dispatches the message to the
        per-command handlers and the main handler.
        """
        try:
            self.dispatch_message(msg)
        except Exception as e:
            on_exception.send(self, e=e)

    def handle_msg(self, msg):
        """Called when a message is received."""
        pass

    def handle_privmsg(self, msg):
        """Called when a message with a PRIVMSG command is received."""
        pass


class AdminMessageDispatcherMixin(BaseMessageDispatcherMixin):
    """Dispatches all messages received via `admin_message_in` signal to the
    proper methods.

    When a message is received via the `admin_message_in` signal:
        Each incomming PRIVMSG is dispatched to the `handle_admin_privmsg`
        method. If a message starts with a command_prefix defined in the config
        it will be also sent to a proper handler, for example
        `admin_command_help`.
    """

    # Prefix for admin command handlers. For example a method
    # `admin_command_help` would be a handler for messages starting with .help
    # received from an admin
    admin_handler_prefix = 'admin_command_'

    def __init__(self, config):
        super(AdminMessageDispatcherMixin, self).__init__(config)
        admin_message_in.connect(self.on_admin_message_in)

    def dispatch_admin_message(self, msg):
        """Dispatches a message originating from an admin to all handlers."""
        # Main handler
        if msg.command == 'PRIVMSG':
            # PRIVMSG handler
            self.handle_admin_privmsg(msg)
            # Command-specific handler
            if self.is_command(msg):
                cmd_name = self.get_command_name(msg)
                func = self._get_command_handler(self.admin_handler_prefix, cmd_name)
                if func is not None:
                    func(msg)

    def on_admin_message_in(self, sender, msg):
        """Handler for an admin_message_in signal. Dispatches the message to the
        per-command handlers and the main handler.
        """
        try:
            self.dispatch_admin_message(msg)
        except Exception as e:
            on_exception.send(self, e=e)

    def handle_admin_privmsg(self, msg):
        """Called when a message with a PRIVMSG command originating from an
        admin is received.
        """
        pass


class MessageDispatcherMixin(AdminMessageDispatcherMixin, StandardMessageDispatcherMixin):
    """Dispatches all messages received via `message_in` and `admin_message_in`
    signals to the proper methods."""
    pass
