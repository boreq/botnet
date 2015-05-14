
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
