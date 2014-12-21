import socket
import ssl
from . import BaseModule
from ..message import Message
from ..signals import message_in, message_out


class IRC(BaseModule):
    """Connects to an IRC server, sends and receives commands.
    
    Example config:

        "irc": {
            "server": "irc.example.com",
            "port": 6667,
            "ssl": false,
            "nick": "my_bot",
            "channels": [
                {
                    "name": "#my-channel",
                    "password": null
                }
            ]
        }

    """

    deltatime = 5

    def __init__(self, config):
        super(IRC, self).__init__(config)
        # Other modules can send commands by sending this signal
        message_out.connect(self.on_message_out)
        # Easier way to access a part of the main config
        self.config = config.get_for_module('irc')
        self.soc = None
        self._partial_data = None

    def stop(self, *args, **kwargs):
        super(IRC, self).stop(*args, **kwargs)
        self.disconnect()

    def on_message_out(self, *args, **kwargs):
        """Handler for the message_out signal."""
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
        # If command is a numeric code convert it to a string
        code = msg.command_code()
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
        """Sends a text to the socket."""
        if len(text) > 0 and self.soc:
            self.logger.debug('Sending:  %s', text)
            text = '%s\r\n' % text
            text = text.encode('utf-8')
            self.soc.send(text)

    def connect(self):
        """Initiates the connection."""
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.config['ssl']:
            self.soc = ssl.wrap_socket(self.soc)
        else:
            self.logger.warning('SSL disabled')
        self.soc.connect((self.config['server'], self.config['port']))

    def disconnect(self):
        self.send('QUIT :Disconnecting')

    def identify(self):
        """Identifies with a server."""
        self.send('NICK ' + self.config['nick'])
        self.send('USER bot bot bot :Python bot')

    def join(self):
        """Joins all channels defined in the config."""
        for channel in self.config['channels']:
            msg = 'JOIN ' + channel['name']
            if channel['password'] is not None:
                msg += ' ' + channel['password']
            self.send(msg)

    def update(self):
        """Main method which should be called."""
        self.logger.debug('Update')
        try:
            self.connect()
            self.identify()
            while not self.stop_event.is_set():
                data = self.soc.recv(4096)
                if not data:
                    break
                data = self.process_data(data)
                for msg in data:
                    msg = self.process_message(msg)
                    self.handle_message(msg)
            self.disconnect()
        finally:
            if self.soc:
                self.soc.close()


mod = IRC
