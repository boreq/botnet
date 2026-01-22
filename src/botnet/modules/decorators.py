from typing import Protocol, Any
from botnet.message import IncomingPrivateMessage
from .base import AuthContext
from functools import wraps


_ATTR_COMMAND_NAME = '_command_name'
_ATTR_PREDICATES = '_predicates'


class Predicate(Protocol):
    def __call__(self, module: Any, msg: IncomingPrivateMessage, auth: AuthContext) -> bool:
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
    def decorator(f):
        setattr(f, _ATTR_COMMAND_NAME, name)

        @wraps(f)
        def decorated_function(self, *args, **kwargs):
            f(self, *args, **kwargs)

        return decorated_function

    return decorator


def predicates(predicates: list[Predicate]):
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

        @wraps(f)
        def decorated_function(self, *args, **kwargs):
            f(self, *args, **kwargs)

        return decorated_function

    return decorator


def _any_group(groups: list[str]):
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
