import argparse
import inspect
from functools import wraps
from typing import Any
from typing import Callable
from typing import cast

from botnet.codes import Code
from botnet.message import IncomingJoin
from botnet.message import IncomingKick
from botnet.message import IncomingPart
from botnet.message import IncomingPrivateMessage
from botnet.message import IncomingQuit
from botnet.message import Message
from botnet.message import MessageCommand

from .base import AuthContext

_ATTR_COMMAND_NAME = '_command_name'
_ATTR_PREDICATES = '_predicates'
_ATTR_MESSAGE_HANDLER = '_message_handler'
_ATTR_AUTH_MESSAGE_HANDLER = '_auth_message_handler'


class Args(dict[str, list[str]]):

    def __init__(self, namespace: argparse.Namespace) -> None:
        super().__init__()
        for name in dir(namespace):
            if not name.startswith('_'):
                value = getattr(namespace, name)
                if not callable(value):
                    self[name] = value


CommandHandler = Callable[[Any, IncomingPrivateMessage, AuthContext], None]
CommandHandlerWithArgs = Callable[[Any, IncomingPrivateMessage, AuthContext, Args], None]
Predicate = Callable[[Any, IncomingPrivateMessage, AuthContext], bool]


def command(name: str) -> Callable[[CommandHandler], CommandHandler]:
    """Decorator which marks methods as commands.

    Example:

        @command('hello')
        def command_hello(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
            self.respond(msg, 'Hello world!')

        @command('admin_hello')
        def command_admin_hello(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
            if 'admin' in auth.groups:
                self.respond(msg, 'Hello world, admin!')
    """
    def decorator(f: CommandHandler) -> CommandHandler:
        setattr(f, _ATTR_COMMAND_NAME, name)
        return f

    return decorator


MessageHandler = Callable[[Any, Message], None]
JoinMessageHandler = Callable[[Any, IncomingJoin], None]
PartMessageHandler = Callable[[Any, IncomingPart], None]
QuitMessageHandler = Callable[[Any, IncomingQuit], None]
KickMessageHandler = Callable[[Any, IncomingKick], None]
PrivateMessageMessageHandler = Callable[[Any, IncomingPrivateMessage], None]

AuthMessageHandler = Callable[[Any, Message, AuthContext], None]
AuthJoinMessageHandler = Callable[[Any, IncomingJoin, AuthContext], None]
AuthPartMessageHandler = Callable[[Any, IncomingPart, AuthContext], None]
AuthQuitMessageHandler = Callable[[Any, IncomingQuit, AuthContext], None]
AuthKickMessageHandler = Callable[[Any, IncomingKick, AuthContext], None]
AuthPrivateMessageMessageHandler = Callable[[Any, IncomingPrivateMessage, AuthContext], None]


def message_handler() -> Callable[[MessageHandler], MessageHandler]:
    """Decorator which marks methods as JOIN message handlers."""
    def decorator(f: MessageHandler) -> MessageHandler:
        setattr(f, _ATTR_MESSAGE_HANDLER, True)
        return f

    return decorator


def reply_handler(code: Code) -> Callable[[MessageHandler], MessageHandler]:
    """Decorator which marks methods as server reply handlers."""
    def decorator(f: MessageHandler) -> MessageHandler:
        setattr(f, _ATTR_MESSAGE_HANDLER, True)

        @wraps(f)
        def wrapped(self: Any, msg: Message) -> None:
            if msg.command_code is not None:
                if msg.command_code != code:
                    return
            f(self, msg)

        return wrapped

    return decorator


def join_message_handler() -> Callable[[JoinMessageHandler], MessageHandler]:
    """Decorator which marks methods as JOIN message handlers."""
    def decorator(f: JoinMessageHandler) -> MessageHandler:
        setattr(f, _ATTR_MESSAGE_HANDLER, True)

        @wraps(f)
        def wrapped(self: Any, msg: Message) -> None:
            if msg.command != MessageCommand.JOIN.value:
                return
            join = IncomingJoin.new_from_message(msg)
            f(self, join)

        return wrapped

    return decorator


def part_message_handler() -> Callable[[PartMessageHandler], MessageHandler]:
    """Decorator which marks methods as PART message handlers."""
    def decorator(f: PartMessageHandler) -> MessageHandler:
        setattr(f, _ATTR_MESSAGE_HANDLER, True)

        @wraps(f)
        def wrapped(self: Any, msg: Message) -> None:
            if msg.command != MessageCommand.PART.value:
                return
            part = IncomingPart.new_from_message(msg)
            f(self, part)

        return wrapped

    return decorator


def quit_message_handler() -> Callable[[QuitMessageHandler], MessageHandler]:
    """Decorator which marks methods as QUIT message handlers."""
    def decorator(f: QuitMessageHandler) -> MessageHandler:
        setattr(f, _ATTR_MESSAGE_HANDLER, True)

        @wraps(f)
        def wrapped(self: Any, msg: Message) -> None:
            if msg.command != MessageCommand.QUIT.value:
                return
            quit = IncomingQuit.new_from_message(msg)
            f(self, quit)

        return wrapped

    return decorator


def kick_message_handler() -> Callable[[KickMessageHandler], MessageHandler]:
    """Decorator which marks methods as KICK message handlers."""
    def decorator(f: KickMessageHandler) -> MessageHandler:
        setattr(f, _ATTR_MESSAGE_HANDLER, True)

        @wraps(f)
        def wrapped(self: Any, msg: Message) -> None:
            if msg.command != MessageCommand.KICK.value:
                return
            kick = IncomingKick.new_from_message(msg)
            f(self, kick)

        return wrapped

    return decorator


def privmsg_message_handler() -> Callable[[PrivateMessageMessageHandler], MessageHandler]:
    """Decorator which marks methods as PRIVMSG message handlers."""
    def decorator(f: PrivateMessageMessageHandler) -> MessageHandler:
        setattr(f, _ATTR_MESSAGE_HANDLER, True)

        @wraps(f)
        def wrapped(self: Any, msg: Message) -> None:
            if msg.command != MessageCommand.PRIVMSG.value:
                return
            privmsg = IncomingPrivateMessage.new_from_message(msg)
            f(self, privmsg)

        return wrapped

    return decorator


def auth_message_handler() -> Callable[[AuthMessageHandler], AuthMessageHandler]:
    """Decorator which marks methods as authenticated JOIN message handlers."""
    def decorator(f: AuthMessageHandler) -> AuthMessageHandler:
        setattr(f, _ATTR_AUTH_MESSAGE_HANDLER, True)
        return f

    return decorator


def auth_join_message_handler() -> Callable[[AuthJoinMessageHandler], AuthMessageHandler]:
    """Decorator which marks methods as authenticated JOIN message handlers."""
    def decorator(f: AuthJoinMessageHandler) -> AuthMessageHandler:
        setattr(f, _ATTR_AUTH_MESSAGE_HANDLER, True)

        @wraps(f)
        def wrapped(self: Any, msg: Message, auth: AuthContext) -> None:
            if msg.command != MessageCommand.JOIN.value:
                return
            join = IncomingJoin.new_from_message(msg)
            f(self, join, auth)

        return wrapped

    return decorator


def auth_part_message_handler() -> Callable[[AuthPartMessageHandler], AuthMessageHandler]:
    """Decorator which marks methods as authenticated PART message handlers."""
    def decorator(f: AuthPartMessageHandler) -> AuthMessageHandler:
        setattr(f, _ATTR_AUTH_MESSAGE_HANDLER, True)

        @wraps(f)
        def wrapped(self: Any, msg: Message, auth: AuthContext) -> None:
            if msg.command != MessageCommand.PART.value:
                return
            part = IncomingPart.new_from_message(msg)
            f(self, part, auth)

        return wrapped

    return decorator


def auth_quit_message_handler() -> Callable[[AuthQuitMessageHandler], AuthMessageHandler]:
    """Decorator which marks methods as authenticated QUIT message handlers."""
    def decorator(f: AuthQuitMessageHandler) -> AuthMessageHandler:
        setattr(f, _ATTR_AUTH_MESSAGE_HANDLER, True)

        @wraps(f)
        def wrapped(self: Any, msg: Message, auth: AuthContext) -> None:
            if msg.command != MessageCommand.QUIT.value:
                return
            quit = IncomingQuit.new_from_message(msg)
            f(self, quit, auth)

        return wrapped

    return decorator


def auth_kick_message_handler() -> Callable[[AuthKickMessageHandler], AuthMessageHandler]:
    """Decorator which marks methods as authenticated KICK message handlers."""
    def decorator(f: AuthKickMessageHandler) -> AuthMessageHandler:
        setattr(f, _ATTR_AUTH_MESSAGE_HANDLER, True)

        @wraps(f)
        def wrapped(self: Any, msg: Message, auth: AuthContext) -> None:
            if msg.command != MessageCommand.KICK.value:
                return
            kick = IncomingKick.new_from_message(msg)
            f(self, kick, auth)

        return wrapped

    return decorator


def auth_privmsg_message_handler() -> Callable[[AuthPrivateMessageMessageHandler], AuthMessageHandler]:
    """Decorator which marks methods as authenticated PRIVMSG message handlers."""
    def decorator(f: AuthPrivateMessageMessageHandler) -> AuthMessageHandler:
        setattr(f, _ATTR_AUTH_MESSAGE_HANDLER, True)

        @wraps(f)
        def wrapped(self: Any, msg: Message, auth: AuthContext) -> None:
            if msg.command != MessageCommand.PRIVMSG.value:
                return
            privmsg = IncomingPrivateMessage.new_from_message(msg)
            f(self, privmsg, auth)

        return wrapped

    return decorator


def predicates(predicates: list[Predicate]) -> Callable[[CommandHandler], CommandHandler]:
    """Decorator which adds predicates which must be fulfilled to launch this command.

    Example:

        def admin_only_predicate(module: Any, msg: IncomingPrivateMessage, auth: AuthContext) -> bool:
            return 'admin' in auth.groups

        @command('hello')
        @predicates([admin_only_predicate])
        def command_admin_hello(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
            assert 'admin' in auth.groups
            self.respond(msg, 'Hello admin!')
    """
    def decorator(f: CommandHandler) -> CommandHandler:
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


def only_admins() -> Callable[[CommandHandler], CommandHandler]:
    """Decorator which makes the command accessible only to admins.

    Example:

        @command('hello')
        @only_admins()
        def command_admin_hello(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
            self.respond(msg, 'Hello admin!')
    """
    return _any_group(['admin'])


def parse_command(params: list[tuple[str, int | str]]) -> Callable[[CommandHandlerWithArgs], CommandHandler]:
    """Decorator which parses the last argument of PRIVMSG, which is the
    message itself, using argparse.

        @parse_command([('person', '1'), ('colors', '+')])
        def command_colors(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
            colors = ' '.join(args['colors'])
            self.respond(msg, '%s likes those colors: %s' % (args['person'][0], colors))

    """
    params.insert(0, ('command', 1))
    parser = argparse.ArgumentParser(exit_on_error=False)
    for name, nargs in params:
        parser.add_argument(name, nargs=nargs)

    def decorator(f: CommandHandlerWithArgs) -> CommandHandler:
        sig = inspect.signature(f)
        if 'args' not in sig.parameters.keys():
            raise Exception('function signature is missing args')
        new_params = [p for name, p in sig.parameters.items() if name != 'args']

        @wraps(f)
        def decorated_function(self: Any, msg: IncomingPrivateMessage, auth: AuthContext, *args: Any, **kwargs: Any) -> None:
            try:
                namespace = parser.parse_args(msg.text.s.split())
            except argparse.ArgumentError:
                return
            f(self, msg, auth, Args(namespace), *args, **kwargs)

        setattr(decorated_function, '__signature__', sig.replace(parameters=new_params))
        return cast(CommandHandler, decorated_function)
    return decorator
