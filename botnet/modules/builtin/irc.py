import datetime
import socket
import ssl
import threading
import time
from ...logging import get_logger
from ...message import Message
from ...signals import message_in, message_out, on_exception
from .. import BaseModule, parse_command
from ..mixins import AdminMessageDispatcherMixin, ConfigMixin


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

    def __enter__(self):
        message_in.connect(self.on_message_in)
        self._set_timers()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        message_in.disconnect(self.on_message_in)
        self._clear_timers()

    def _clear_timers(self):
        """Cancel scheduled execution of the timers."""
        for timer in [self._timer_ping, self._timer_abort]:
            if timer is not None:
                timer.cancel()

    def _set_timers(self):
        """Schedule the execution of the timers."""
        self._timer_ping = threading.Timer(self.ping_timeout, self.on_timer_ping)
        self._timer_abort = threading.Timer(self.abort_timeout, self.on_timer_abort)
        self._timer_ping.start()
        self._timer_abort.start()

    def _reset_timers(self):
        """Reschedule the execution of the timers."""
        self._clear_timers()
        self._set_timers()

    def on_message_in(self, sender, msg):
        self._reset_timers()

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


class IRC(AdminMessageDispatcherMixin, ConfigMixin, BaseModule):
    """Connects to an IRC server, sends and receives commands.

    Example module config:

        "botnet": {
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
        }

    """

    deltatime = 5

    def __init__(self, config):
        super(IRC, self).__init__(config)
        self.register_config('botnet', 'base_responder')
        self.register_config('botnet', 'irc')
        self.soc = None
        self._partial_data = None
        message_out.connect(self.on_message_out)

    def get_command_prefix(self):
        """This method should return the command prefix."""
        return self.config_get('command_prefix', '.')

    @parse_command([('name', 1), ('password', '?')], launch_invalid=False)
    def admin_command_channel_join(self, msg, args):
        self.join(args.name[0], args.password)

    @parse_command([('name', 1)], launch_invalid=False)
    def admin_command_channel_part(self, msg, args):
        self.part(args.name[0])

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
        try:
            message_in.send(self, msg=msg)
        except Exception as e:
            on_exception.send(self, e=e)

    def handler_rpl_endofmotd(self, msg):
        self.autosend()
        self.join_from_config()

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
            on_exception.send(self, e=e)
        return False

    def connect(self):
        """Initiates the connection."""
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.config_get('ssl'):
            self.soc = ssl.wrap_socket(self.soc)
        else:
            self.logger.warning('SSL disabled')
        self.soc.connect((self.config_get('server'), self.config_get('port')))
        self.soc.settimeout(1)

    def disconnect(self):
        self.send('QUIT :Disconnecting')

    def identify(self):
        """Identifies with a server."""
        self.send('NICK ' + self.config_get('nick'))
        self.send('USER botnet botnet botnet :Python bot')

    def join_from_config(self):
        """Joins all channels defined in the config."""
        for channel in self.config_get('channels'):
            self.join(channel['name'], channel['password'])

    def join(self, channel_name, channel_password):
            msg = 'JOIN ' + channel_name
            if channel_password is not None:
                msg += ' ' + channel_password
            self.send(msg)

    def part(self, channel_name):
            msg = 'PART ' + channel_name
            self.send(msg)

    def autosend(self):
        """Automatically sends commands to a server before joining channels."""
        commands = self.config_get('autosend', [])
        for command in commands:
            self.send(command)
        if len(commands) > 0:
            time.sleep(1)

    def update(self):
        """Main method which should be called."""
        self.logger.debug('Update')
        with InactivityMonitor(self):
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


mod = IRC
