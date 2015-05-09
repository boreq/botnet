import datetime
import socket
import ssl
import threading
import time
from . import BaseModule
from ..logging import get_logger
from ..message import Message
from ..signals import message_in, message_out, on_exception


class InactivityMonitor(object):
    """Checks if the connection is still alive.

    If no messages are received from a server in a certain amount of time PING
    command will be sent. If the server will not respond the entire IRC module
    will be restarted to reestablish the connection.
    """

    # PING command will be sent after that many seconds without communication
    ping_timeout = 60
    # IRC module will be restarted after that many seconds without communication
    abort_timeout = 70

    def __init__(self, irc_module):
        self.logger = get_logger(self)
        self.irc_module = irc_module

        self._timer_ping = None
        self._timer_abort = None

        message_in.connect(self.on_message_in)

    def clear_timers(self):
        """Cancel scheduled execution of the timers."""
        self.logger.debug('clear timers')
        for timer in [self._timer_ping, self._timer_abort]:
            if timer is not None:
                timer.cancel()

    def set_timers(self):
        self.logger.debug('set timers')
        """Schedule the execution of the timers."""
        self._timer_ping = threading.Timer(self.ping_timeout, self.on_timer_ping)
        self._timer_abort = threading.Timer(self.abort_timeout, self.on_timer_abort)
        self._timer_ping.start()
        self._timer_abort.start()

    def reset_timers(self):
        """Reschedule the execution of the timers."""
        self.clear_timers()
        self.set_timers()

    def on_message_in(self, sender, msg):
        self.reset_timers()

    def on_timer_ping(self):
        """Launched by _timer_ping."""
        self.logger.debug('ping the server')
        timestamp = datetime.datetime.now().timestamp()
        msg = Message(command='PING', params=[str(timestamp)])
        message_out.send(self, msg=msg)

    def on_timer_abort(self):
        """Launched by _timer_abort."""
        self.logger.debug('stop the module')
        self.irc_module.stop()


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
            ],
            "autosend": [
                "PRIVMSG NickServ :IDENTIFY pass"
            ]
        }

    """

    deltatime = 5

    def __init__(self, config):
        super(IRC, self).__init__(config)
        message_out.connect(self.on_message_out)
        self.config = config.get_for_module('irc')
        self.soc = None
        self._partial_data = None
        self.inact_monitor = InactivityMonitor(self)

    def stop(self):
        """To stop correctly it is necessary to disconnect from the server
        because blocking sockets are used.
        """
        super(IRC, self).stop()
        self.disconnect()

    def on_message_out(self, sender, msg):
        """Handler for the message_out signal.

        sender: object sending the signal, most likely an other module.
        msg: Message object.
        """
        self.send(msg.to_string())

    def process_data(self, data):
        """Process the data received from the socket.

        Ensures that there is no partial command at the end of the data chunk
        (that can happen if the data does not fit in the socket buffer). If
        that happens the partual command will be reconstructed the next time
        this function is called.

        data: raw data from the socket.
        """
        if not data:
            return []

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

        # Forward the message to other modules
        message_in.send(self, msg=msg)

    def handler_rpl_endofmotd(self, msg):
        self.autosend()
        self.join()

    def handler_ping(self, msg):
        rmsg = Message(command='PONG', params=msg.params)
        self.send(rmsg.to_string())

    def send(self, text):
        """Sends a text to the socket."""
        # To be honest I have never seen an exception here
        try:
            if len(text) > 0 and self.soc:
                self.logger.debug('Sending:  %s', text)
                text = '%s\r\n' % text
                text = text.encode('utf-8')
                self.soc.send(text)
                return True
        except (OSError, ssl.SSLError) as e:
            on_exception(self, e=e)
        return False

    def connect(self):
        """Initiates the connection."""
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.config['ssl']:
            self.soc = ssl.wrap_socket(self.soc)
        else:
            self.logger.warning('SSL disabled')
        self.soc.connect((self.config['server'], self.config['port']))
        self.soc.settimeout(1)

    def disconnect(self):
        self.send('QUIT :Disconnecting')

    def identify(self):
        """Identifies with a server."""
        self.send('NICK ' + self.config['nick'])
        self.send('USER botnet botnet botnet :Python bot')

    def join(self):
        """Joins all channels defined in the config."""
        for channel in self.config['channels']:
            msg = 'JOIN ' + channel['name']
            if channel['password'] is not None:
                msg += ' ' + channel['password']
            self.send(msg)

    def autosend(self):
        """Automatically sends commands to a server before joining channels."""
        commands = self.config.get('autosend', [])
        for command in commands:
            self.send(command)
        if len(commands) > 0:
            time.sleep(1)

    def update(self):
        """Main method which should be called."""
        self.logger.debug('Update')
        try:
            self.connect()
            self.identify()
            while not self.stop_event.is_set():
                try:
                    data = self.soc.recv(4096)
                    if not data:
                        break
                    for line in self.process_data(data):
                        msg = self.process_message(line)
                        self.handle_message(msg)
                except (socket.timeout, ssl.SSLWantReadError) as e:
                    pass
        finally:
            if self.soc:
                self.soc.close()
            self.inact_monitor.clear_timers()


mod = IRC
