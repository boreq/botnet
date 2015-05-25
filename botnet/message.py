"""
    Contains objects related to interpreting messages received from a server.

    http://tools.ietf.org/html/rfc2812#section-2.3
    http://tools.ietf.org/html/rfc2812#section-2.3.1
"""


from .codes import Code


def analyze_prefix(prefix):
    """Analyze a message prefix which is a server name or data about the user
    (nickname, user, host). Returns a tuple containing a servername and
    a nickname (one of those will always be None).

    prefix: message prefix.
    """
    servername = None
    nickname = None
    if prefix is not None:
        parts = prefix.split('!')
        if len(parts) > 1:
            nickname = parts[0]
        else:
            servername = prefix
    return servername, nickname


class Message(object):
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

    def __init__(self, prefix=None, command=None, params=None):
        self.prefix = prefix
        self.command = command.upper() if command is not None else command
        self.params = params or []

    @property
    def servername(self):
        """Calls analyze_prefix on self.prefix in the background."""
        return analyze_prefix(self.prefix)[0]

    @property
    def nickname(self):
        """Calls analyze_prefix on self.prefix in the background."""
        return analyze_prefix(self.prefix)[1]

    def from_string(self, message):
        """Loads a message from a string.

        message: string, for example one line received from the server.
        """
        self.prefix = None
        self.command = None
        self.params = []

        # Load data.
        message = message.strip()
        message = message.split()
        for index, part in enumerate(message):
            # Prefix.
            if index == 0 and part[0] == ':':
                self.prefix = part[1:]
                continue
            # Command.
            if self.command is None:
                self.command = part.upper()
                continue
            # Parameters.
            self.params.append(part)

        # If one parameter starts with a colon (':') it is considered as the
        # last parameter and may contain spaces.
        for index, param in enumerate(self.params):
            if param.startswith(':'):
                # Create a list with params before the one containing a colon.
                params = self.params[:index]
                # Join a parameter with a colon and parameters following it.
                # Remove the first character - a colon.
                params.append(' '.join(self.params[index:])[1:])
                self.params = params
                break

    def to_string(self):
        """Converts the message back to a string."""
        tmp = [self.command.upper()]
        if self.prefix:
            tmp.insert(0, ':%s' % self.prefix)
        for param in self.params:
            if ' ' in param:
                param = ':%s' % param
            tmp.append(param)
        return ' '.join(tmp)

    def command_code(self):
        """Returns an enum which matches a numeric reply code or None if there
        is no such enum or the message is not numeric.
        """
        try:
            return Code(int(self.command))
        except ValueError:
            return None

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return '<Message: %s>' % self.__str__()
