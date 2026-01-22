import argparse
import inspect
from typing import Protocol, Any, Callable, TypeVar
from botnet.message import IncomingPrivateMessage
from .base import AuthContext
from functools import wraps


_ATTR_COMMAND_NAME = '_command_name'
_ATTR_PREDICATES = '_predicates'


T = TypeVar("T", contravariant=True)


class CommandHandler(Protocol[T]):
    def __call__(self, instance: T, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
        ...


class CommandHandlerWithArguments(Protocol[T]):
    def __call__(self, instance: T, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        ...


def command(name: str):
    """Decorator which marks methods as commands. The wrapped method may
    optionally have the following arguments:
        - msg: Message
        - auth: AuthContext

    The arguments must have the same names if they are present. The messages
    passed to those functions are always of kind PRIVMSG.

    Example:

        @command('hello')
        def command_hello(self, msg: Message) -> None:
            self.respond(msg, 'Hello world!')

        @command('admin_hello')
        def command_admin_hello(self, msg: Message, auth: AuthContext) -> None:
            if 'admin' in auth.groups:
                self.respond(msg, 'Hello world, admin!')
    """
    def decorator(f: CommandHandler) -> CommandHandler:
        setattr(f, _ATTR_COMMAND_NAME, name)
        return f

    return decorator


class Predicate(Protocol):
    def __call__(self, module: Any, msg: IncomingPrivateMessage, auth: AuthContext) -> bool:
        ...


def predicates(predicates: list[Predicate]) -> Callable[[CommandHandler], CommandHandler]:
    """Decorator which adds predicates which must be fulfilled to launch this command.

    Example:

        @command('hello')
        @predicates([admin_only_predicate])
        def command_admin_hello(self, msg: Message) -> None:
            self.respond(msg, 'Hello admin!')
    """
    def decorator(f):
        all_predicates = getattr(f, _ATTR_PREDICATES, [])
        all_predicates.extend(predicates)
        setattr(f, _ATTR_PREDICATES, all_predicates)
        return f

    return decorator


def _any_group(groups: list[str]) -> Callable[[CommandHandler], CommandHandler]:
    def predicate(module: Any, msg: IncomingPrivateMessage, auth: AuthContext) -> bool:
        for group in groups:
            if group in auth.groups:
                return True
        return False
    return predicates([predicate])


def only_admins():
    """Decorator which makes the command accessible only to admins.

    Example:

        @command('hello')
        @only_admins()
        def command_admin_hello(self, msg: Message) -> None:
            self.respond(msg, 'Hello admin!')
    """
    return _any_group(['admin'])


class Args(dict[str, list[str]]):

    def __init__(self, namespace: argparse.Namespace) -> None:
        for name in dir(namespace):
            if not name.startswith('_'):
                value = getattr(namespace, name)
                if not callable(value):
                    self[name] = value


def parse_command(params):
    """Decorator which parses the last argument of PRIVMSG, which is the
    message itself, using argparse.

        @parse_command([('person', '1'), ('colors', '+')])
        def command_colors(self, msg, auth, args):
            colors = ' '.join(args['colors'])
            self.respond(msg, '%s likes those colors: %s' % (args['person'][0], colors))

    """
    params.insert(0, ('command', 1))
    parser = argparse.ArgumentParser(exit_on_error=False)
    for name, nargs in params:
        parser.add_argument(name, nargs=nargs)

    def decorator(f):
        sig = inspect.signature(f)
        if 'args' not in sig.parameters.keys():
            raise Exception('function signature is missing args')
        new_params = [p for name, p in sig.parameters.items() if name != 'args']

        @wraps(f)
        def decorated_function(self: Any, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
            try:
                args = parser.parse_args(msg.text.s.split())
            except argparse.ArgumentError:
                return
            f(self, msg, auth, Args(args))

        setattr(decorated_function, '__signature__', sig.replace(parameters=new_params))
        return decorated_function
    return decorator
