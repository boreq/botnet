import argparse
from functools import wraps


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
        import_name = 'botnet.modules.builtin.%s.mod' % module_name
    else:
        import_name = '%s.mod' % module_name
    return import_by_name(import_name)


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
