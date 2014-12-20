import socket
from . import BaseModule
from ..logging import get_logger
from ..message import Message
from ..signals import message_in, message_out


class IRC(BaseModule):
    """Connects to an IRC server, sends and receives commands."""

    def __init__(self, *args, **kwargs):
        super(IRC, self).__init__(*args, **kwargs)
        # Other modules can send commands by sending this signal
        message_out.connect(self.on_message_out)
        # Easier way to access a part of the main config
        self.config = args[0]['module_config']['irc']
        self.logger = get_logger(self)
        self._partial_data = None

    def on_message_out(self, *args, **kwargs):
        self.logger.debug('on_message_out %s %s', args, kwargs)
        self.send(kwargs['msg'].to_string())

    def process_data(self, data):
        """Process the data received from the socket.

        Ensures that there is no partial command at the end of the data chunk
        (that can happen if the data does not fit in the socket buffer). If
        that happens the partual command will be reconstructed the next time
        this function is called.

        data: raw data from the socket.
        """
        data = data.decode()
        lines = data.splitlines()

        # If there is at least one newline in that part this data chunk contains
        # the end of at least one command. If previous command was stored from
        # previous the previous chunk then it is complete now
        if '\n' in data and self._partial_data:
            lines[0] = self._partial_data + lines[0]
            self._partial_data = None

        # Store partial data
        if not data.endswith('\n'):
            if self._partial_data is None:
                self._partial_data = ''
            self._partial_data += lines.pop()

        return lines

    def process_message(self, msg):
        """Process one line received from the server."""
        rw = Message()
        rw.from_string(msg)
        return rw

    def handle_message(self, msg):
        """Process the created Message object."""
        self.logger.debug('Received: %s', str(msg))

        # Forward the message to other modules
        message_in.send(self, msg=msg)

        # Dispatch the message to the right handler
        code = msg.command_code()
        # If command is a numerical code convert it to a string
        if code is not None:
            handler_name = 'handler_%s' % code.name.lower()
        else:
            handler_name = 'handler_%s' % msg.command.lower()
        func = getattr(self, handler_name, None)
        if func is not None:
            self.logger.debug('Dispatching to %s', handler_name)
            func(msg)

    def handler_rpl_endofmotd(self, msg):
        self.join()

    def handler_ping(self, msg):
        self.send('PONG :ping')

    def send(self, text):
        if len(text) > 0:
            self.logger.debug('Sending:  %s', text)
            text = '%s\r\n' % text
            text = text.encode('utf-8')
            self.soc.send(text)

    def connect(self):
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.soc.connect((self.config['server'], self.config['port']))

    def identify(self):
        self.send('NICK ' + self.config['nick'])
        self.send('USER bot bot bot :Python bot')

    def join(self):
        for channel in self.config['channels']:
            msg = 'JOIN ' + channel['name']
            if channel['password'] is not None:
                msg += ' ' + channel['password']
            self.send(msg)

    def update(self):
        """Main method which should be called."""
        self.logger.debug('Update')
        self.connect()
        self.identify()

        while True:
            data = self.soc.recv(4096)
            if not data:
                break
            data = self.process_data(data)
            for msg in data:
                msg = self.process_message(msg)
                self.handle_message(msg)

        self.send('QUIT :Disconnecting')


mod = IRC
