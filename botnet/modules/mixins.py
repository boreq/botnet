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
        actual_key = self._get_config_key(self._config_locations[-1], key)

        # walk
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
        return True

    def config_append(self, key, value):
        """Alias for
            self.config_get(key, auto=[]).append(value)
        """
        try:
            self.config_get(key, auto=[]).append(value)
        except AttributeError as e:
            raise AttributeError('Value for a key "{}" is not a list'.format(key)) from e
        return True
