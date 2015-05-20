import argparse
import importlib
from functools import wraps


def get_module(module_name):
    """Attempts to find a bot module by name. This function looks for a
    Python module named `module_name` located in `botnet.modules`. If the name
    is prefixed with `botnet_` this function will look for an external module
    instead.
    """
    if not module_name.startswith('botnet_'):
        import_name = 'botnet.modules.builtin.%s' % module_name
    else:
        import_name = '%s' % module_name
    return importlib.import_module(import_name)


def reload_module(module):
    """Reloads a loaded Python module."""
    importlib.reload(module)


def get_ident_string(module_class):
    """Returns a string which can be used to identify a module class.
    Normal comparison marks the same class as different after reloading its
    parent module.
    """
    return module_class.__module__ + "." + module_class.__name__


def parse_command(params, launch_invalid=True):
    """Decorator. Automatically parses the last argument of PRIVMSG, which is
    the message itself, using argparse. If launch_invalid is True the function
    will be launched if the parameters are invalid.

        class TestResponder(BaseResponder):
            @parse_command([('person', '?'), ('colors', '+')])
            def command_colors(self, msg, args):
                colors = ' '.join(args.colors)
                self.respond(msg, '%s likes those colors: %s' % (args.person,
                                                                 colors))

    """
    params.insert(0, ('command', 1))
    parser = argparse.ArgumentParser()
    for name, nargs in params:
        parser.add_argument(name, nargs=nargs)

    def decorator(f):
        @wraps(f)
        def decorated_function(self, msg):
            args = msg.params[-1].split()
            try:
                args = parser.parse_args(args)
            except SystemExit:
                args = None
            if not launch_invalid and args is None:
                return
            f(self, msg, args)
        return decorated_function
    return decorator
