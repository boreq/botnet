import argparse
import inspect
from functools import wraps
from typing import Protocol, Any
from ...message import Message
from ..base import AuthContext


class CommandHandlerWithArguments(Protocol):
    def __call__(self, instance: Any, msg: Message, auth: AuthContext, args: Any) -> None:
        ...


def parse_command(params):
    """Decorator which parses the last argument of PRIVMSG, which is the
    message itself, using argparse.

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

    def decorator(f: CommandHandlerWithArguments):
        sig = inspect.signature(f)
        if 'args' not in sig.parameters.keys():
            raise Exception('function signature is missing args')
        new_params = [p for name, p in sig.parameters.items() if name != 'args']

        @wraps(f)
        def decorated_function(self, msg: Message, auth: AuthContext):
            args = msg.params[-1].split()
            try:
                args = parser.parse_args(args)
            except SystemExit:
                return

            f(self, msg, auth, args)

        setattr(decorated_function, '__signature__', sig.replace(parameters=new_params))
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
