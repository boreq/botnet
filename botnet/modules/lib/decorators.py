import argparse
from functools import wraps


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


def catch_other(exception, default_text):
    """Decorator which catches exceptions which don't inherit from the exception
    class and throws that exception instead.

    exception: exception class.
    default_text: when an exception is replaced the new exception will be
                  initialized with this error message.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except exception:
                raise
            except Exception:
                raise exception(default_text)
        return decorated_function
    return decorator
