"""
    Contains objects related to interpreting messages received from a server.

    https://tools.ietf.org/html/rfc2812#section-2.3
    https://tools.ietf.org/html/rfc2812#section-2.3.1
"""


import re
from enum import Enum

from .codes import Code


class Message:
    """Parses the server message and provides access to its properties.

    Properties you can access are the same as constructor parameters.
    Additionaly servername and nickname are available to quickly check the
    source of a message.

    prefix: message prefix. Prefix is None if not present in the message.
    command: message command (string with a word or 3 digit number),
             is stored as uppercase (is converted to uppercase by
             from_string and constructor).
    params: message parameters. Always a list.
    """
    prefix: str | None
    command: str
    params: list[str]

    def __init__(self, command: str, prefix: str | None = None, params: list[str] = []) -> None:
        self.prefix = prefix
        self.command = command.upper()
        self.params = params or []

    @classmethod
    def new_from_string(cls, message: str) -> Message:
        """Loads a message from a string.

        message: string, for example one line received from the server.
        """
        prefix = None
        command = None
        params = []

        # Load data.
        message = message.strip()
        for index, part in enumerate(message.split(' ')):
            # Prefix.
            if index == 0 and part[0] == ':':
                prefix = part[1:]
                continue

            # Command.
            if command is None:
                command = part.upper()
                continue
            # Parameters.
            params.append(part)

        # If one parameter starts with a colon (':') it is considered as the
        # last parameter and may contain spaces.
        for index, param in enumerate(params):
            if param.startswith(':'):
                # Create a list with params before the one containing a colon.
                tmpparams = params[:index]
                # Join a parameter with a colon and parameters following it.
                # Remove the first character - a colon.
                tmpparams.append(' '.join(params[index:])[1:])
                params = tmpparams
                break

        assert command is not None
        return Message(prefix=prefix, command=command, params=params)

    @property
    def servername(self) -> str | None:
        """Calls analyze_prefix on self.prefix in the background."""
        return self._analyze_prefix(self.prefix)[0]

    @property
    def nickname(self) -> str | None:
        """Calls analyze_prefix on self.prefix in the background."""
        return self._analyze_prefix(self.prefix)[1]

    @property
    def command_code(self) -> Code | None:
        """Returns an enum which matches a numeric reply code or None if there
        is no such enum or the message is not numeric.
        """
        try:
            return Code(int(self.command))
        except ValueError:
            return None

    def to_string(self) -> str:
        """Converts the message back to a string."""
        tmp = [self.command.upper()]
        if self.prefix:
            tmp.insert(0, ':%s' % self.prefix)
        for param in self.params:
            if ' ' in param or ':' in param:
                param = ':%s' % param
            tmp.append(param)
        return ' '.join(tmp)

    def __str__(self) -> str:
        return self.to_string()

    def __repr__(self) -> str:
        return '<Message: %s>' % self.__str__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Message):
            raise NotImplementedError
        return self.prefix == other.prefix and self.command == other.command and self.params == other.params

    def _analyze_prefix(self, prefix: str | None) -> tuple[str | None, str | None]:
        """Analyze a message prefix which is a server name or data about the user
        (nickname, user, host). Returns a tuple containing a servername and
        a nickname (one of those will always be None).

        prefix: message prefix.
        """
        if prefix is None:
            return None, None

        parts = prefix.split('!')
        if len(parts) > 1:
            return None, parts[0]
        else:
            return prefix, None


_NICK_REGEX = re.compile(r"^[a-zA-Z\[\]\\`_^{}][a-zA-Z0-9\[\]\\`_^{}|-]{0,31}$")


class Nick:
    s: str

    def __init__(self, s: str) -> None:
        if s is None or s == '':
            raise Exception('nick cannot be none or empty')

        if not _NICK_REGEX.match(s):
            raise Exception(f'nick \'{s}\' is invalid')

        self.s = s

    def __str__(self) -> str:
        return self.s

    def __repr__(self) -> str:
        return f'\'{self.s}\''

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Nick):
            raise NotImplementedError
        return self.s.lower() == other.s.lower()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Nick):
            raise NotImplementedError
        return self.s.lower() < other.s.lower()

    def __hash__(self) -> int:
        return hash(self.s.lower())


_CHANNEL_REGEX = re.compile(r"^[#&+\!][^ \x07,]{1,49}$")


class Channel:
    s: str

    def __init__(self, s: str) -> None:
        if s is None or s == '':
            raise Exception('channel cannot be none or empty')

        if not _CHANNEL_REGEX.match(s):
            raise Exception(f'channel \'{s}\' is invalid')

        self.s = s

    def __str__(self) -> str:
        return self.s

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Channel):
            raise NotImplementedError
        return self.s.lower() == other.s.lower()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Channel):
            raise NotImplementedError
        return self.s.lower() < other.s.lower()

    def __hash__(self) -> int:
        return hash(self.s.lower())


def _is_channel_name(text: str | None) -> bool:
    if text:
        return text[0] in ['&', '#', '+', '!']
    return False


class Target:
    nick_or_channel: Nick | Channel

    def __init__(self, nick_or_channel: Nick | Channel) -> None:
        assert isinstance(nick_or_channel, Nick) or isinstance(nick_or_channel, Channel)
        self.nick_or_channel = nick_or_channel

    @classmethod
    def new_from_string(cls, s: str) -> Target:
        if _is_channel_name(s):
            return cls(Channel(s))
        else:
            return cls(Nick(s))

    @property
    def is_channel(self) -> bool:
        return isinstance(self.nick_or_channel, Channel)

    @property
    def is_nick(self) -> bool:
        return isinstance(self.nick_or_channel, Nick)

    @property
    def channel(self) -> Channel | None:
        if self.is_channel:
            assert isinstance(self.nick_or_channel, Channel)
            return self.nick_or_channel
        return None

    @property
    def nick(self) -> Nick | None:
        if self.is_nick:
            assert isinstance(self.nick_or_channel, Nick)
            return self.nick_or_channel
        return None

    def __str__(self) -> str:
        return self.nick_or_channel.s

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Target):
            raise NotImplementedError
        return self.nick_or_channel == other.nick_or_channel


class Text:
    s: str

    def __init__(self, s: str) -> None:
        if s is None or s == '':
            raise Exception('text cannot be none or empty')

        self.s = s

    def __str__(self) -> str:
        return self.s

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Text):
            raise NotImplementedError
        return self.s == other.s


class MessageCommand(Enum):
    PRIVMSG = 'PRIVMSG'
    JOIN = 'JOIN'
    PART = 'PART'
    KICK = 'KICK'
    QUIT = 'QUIT'
    PING = 'PING'


class IncomingPrivateMessage:
    sender: Nick
    target: Target
    text: Text

    def __init__(self, sender: Nick, target: Target, text: Text) -> None:
        self.sender = sender
        self.target = target
        self.text = text

    @classmethod
    def new_from_message(cls, msg: Message) -> IncomingPrivateMessage:
        if msg.command != MessageCommand.PRIVMSG.value:
            raise Exception('passed a message that isn\'t a PRIVMSG')

        if msg.nickname is None:
            raise Exception('a received PRIVMSG should have a nickname available')

        if len(msg.params) != 2:
            raise Exception('a received PRIVMSG should have two parameters')

        sender = Nick(msg.nickname)
        target = Target.new_from_string(msg.params[0])
        text = Text(msg.params[1])
        return cls(sender, target, text)

    def __repr__(self) -> str:
        return f'<IncomingPrivateMessage: sender={self.sender} target={self.target} text={self.text}>'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IncomingPrivateMessage):
            raise NotImplementedError
        return self.sender == other.sender and self.target == other.target and self.text == other.text


class IncomingJoin:
    nick: Nick
    channel: Channel

    def __init__(self, nick: Nick, channel: Channel) -> None:
        self.nick = nick
        self.channel = channel

    @classmethod
    def new_from_message(cls, msg: Message) -> IncomingJoin:
        if msg.command != MessageCommand.JOIN.value:
            raise Exception('passed a message that isn\'t a JOIN')

        if msg.nickname is None:
            raise Exception('a received JOIN should have a nickname available')

        if len(msg.params) != 1:
            raise Exception('a received JOIN should have one parameter')

        nick = Nick(msg.nickname)
        channel = Channel(msg.params[0])
        return cls(nick, channel)

    def __repr__(self) -> str:
        return f'<IncomingJoin: nick={self.nick} channel={self.channel}>'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IncomingJoin):
            raise NotImplementedError
        return self.nick == other.nick and self.channel == other.channel


class IncomingPart:
    nick: Nick
    channel: Channel
    part_message: str | None

    def __init__(self, nick: Nick, channel: Channel, part_message: str | None) -> None:
        self.nick = nick
        self.channel = channel
        self.part_message = part_message

    @classmethod
    def new_from_message(cls, msg: Message) -> IncomingPart:
        if msg.command != MessageCommand.PART.value:
            raise Exception('passed a message that isn\'t a PART')

        if msg.nickname is None:
            raise Exception('a received PART should have a nickname available')

        if len(msg.params) < 1 or len(msg.params) > 2:
            raise Exception('a received PART should have 1 or 2 parameters')

        nick = Nick(msg.nickname)
        channel = Channel(msg.params[0])

        if len(msg.params) == 2:
            part_message = msg.params[1]
        else:
            part_message = None

        return cls(nick, channel, part_message)

    def __repr__(self) -> str:
        return f'<IncomingPart: nick={self.nick} channel={self.channel} part_message={self.part_message}>'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IncomingPart):
            raise NotImplementedError
        return self.nick == other.nick and self.channel == other.channel and self.part_message == other.part_message


class IncomingKick:
    kicker: Nick
    channel: Channel
    kickee: Nick
    kick_message: str | None

    def __init__(self, kicker: Nick, channel: Channel, kickee: Nick, kick_message: str | None) -> None:
        self.kicker = kicker
        self.channel = channel
        self.kickee = kickee
        self.kick_message = kick_message

    @classmethod
    def new_from_message(cls, msg: Message) -> IncomingKick:
        if msg.command != MessageCommand.KICK.value:
            raise Exception('passed a message that isn\'t a KICK')

        if msg.nickname is None:
            raise Exception('a received KICK should have a nickname available')

        if len(msg.params) < 2 or len(msg.params) > 3:
            raise Exception('a received KICK should have 2 or 3 parameters')

        kicker = Nick(msg.nickname)
        channel = Channel(msg.params[0])
        kickee = Nick(msg.params[1])

        if len(msg.params) == 3:
            kick_message = msg.params[2]
        else:
            kick_message = None

        return cls(kicker, channel, kickee, kick_message)

    def __repr__(self) -> str:
        return f'<IncomingKick: kicker={self.kicker} channel={self.channel} kickee={self.kickee} kick_message={self.kick_message}>'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IncomingKick):
            raise NotImplementedError
        return self.kicker == other.kicker and self.channel == other.channel and self.kickee == other.kickee and self.kick_message == other.kick_message


class IncomingQuit:
    nick: Nick
    quit_message: str | None

    def __init__(self, nick: Nick, quit_message: str | None) -> None:
        self.nick = nick
        self.quit_message = quit_message

    @classmethod
    def new_from_message(cls, msg: Message) -> IncomingQuit:
        if msg.command != MessageCommand.QUIT.value:
            raise Exception('passed a message that isn\'t a QUIT')

        if msg.nickname is None:
            raise Exception('a received QUIT should have a nickname available')

        nick = Nick(msg.nickname)

        if len(msg.params) > 1:
            raise Exception('a received QUIT should have no parameters or 1 parameter')

        if len(msg.params) == 1:
            quit_message = msg.params[0]
        else:
            quit_message = None

        return cls(nick, quit_message)

    def __repr__(self) -> str:
        return f'<IncomingQuit: nick={self.nick} quit_message={self.quit_message}>'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IncomingQuit):
            raise NotImplementedError
        return self.nick == other.nick and self.quit_message == other.quit_message


class IncomingPing:
    params: list[str]

    def __init__(self, params: list[str]) -> None:
        if len(params) == 0:
            raise Exception('ping needs at least one parameter')
        self.params = params

    @classmethod
    def new_from_message(cls, msg: Message) -> IncomingPing:
        if msg.command != MessageCommand.PING.value:
            raise Exception('passed a message that isn\'t a PING')

        if len(msg.params) < 1:
            raise Exception('a received PING should have at least 1 parameter')

        return cls(msg.params)

    def __repr__(self) -> str:
        return f'<IncomingPing: params={self.params}>'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IncomingPing):
            raise NotImplementedError
        return self.params == other.params
