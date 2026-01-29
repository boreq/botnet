import datetime
import fnmatch
import select
import socket
import ssl
import threading
from dataclasses import dataclass
from typing import Any
from typing import Generator
from typing import Protocol

from ...codes import Code
from ...config import Config
from ...logging import get_logger
from ...message import IncomingPing
from ...message import IncomingPrivateMessage
from ...message import Message
from ...modules import reply_handler
from ...signals import message_in
from ...signals import message_out
from ...signals import on_exception
from .. import Args
from .. import AuthContext
from .. import BaseResponder
from .. import command
from .. import only_admins
from .. import parse_command
from .. import ping_message_handler


class Restarter(Protocol):
    def restart(self) -> None:
        ...


class NoopWith:

    def __enter__(self) -> NoopWith:
        return self

    def __exit__(self, exception_type: Any, exception_value: Any, traceback: Any) -> None:
        pass


class InactivityMonitor:
    """Checks if the connection is still alive.

    If no messages are received from a server in a certain amount of time PING
    command will be sent. If the server will not respond the entire IRC module
    will be restarted to reestablish the connection.
    """

    # PING command will be sent after that many seconds without communication
    ping_timeout: float = 60

    # PING command will continue to be be resent in those intervals after the
    # initial PING command
    ping_repeat: float = 10

    # IRC module will be restarted after that many seconds without communication
    abort_timeout: float = 240

    def __init__(self, restarter: Restarter):
        self.logger = get_logger(self)
        self.restarter = restarter

        self._timer_ping: threading.Timer | None = None
        self._timer_abort: threading.Timer | None = None

    def __enter__(self) -> InactivityMonitor:
        message_in.connect(self.on_message_in)
        self._set_timers()
        return self

    def __exit__(self, exception_type: Any, exception_value: Any, traceback: Any) -> None:
        message_in.disconnect(self.on_message_in)
        self._clear_timers()

    def _clear_timers(self) -> None:
        """Cancel scheduled execution of the timers."""
        for timer in [self._timer_ping, self._timer_abort]:
            if timer is not None:
                timer.cancel()

    def _set_ping(self, timeout: float) -> None:
        self._timer_ping = threading.Timer(timeout, self.on_timer_ping)
        self._timer_ping.start()

    def _set_abort(self, timeout: float) -> None:
        self._timer_abort = threading.Timer(timeout, self.on_timer_abort)
        self._timer_abort.start()

    def _set_timers(self) -> None:
        """Schedule the execution of the timers."""
        self._set_ping(self.ping_timeout)
        self._set_abort(self.abort_timeout)

    def _reset_timers(self) -> None:
        """Reschedule the execution of the timers."""
        self._clear_timers()
        self._set_timers()

    def on_message_in(self, sender: Any, msg: Message) -> None:
        self._reset_timers()

    def on_timer_ping(self) -> None:
        """Launched by _timer_ping."""
        self.logger.debug('ping the server')
        timestamp = self._now().timestamp()
        msg = Message(command='PING', params=[str(timestamp)])
        message_out.send(self, msg=msg)
        self._set_ping(self.ping_repeat)

    def on_timer_abort(self) -> None:
        """Launched by _timer_abort."""
        self.logger.debug('restart the connection')
        self.restarter.restart()

    def _now(self) -> datetime.datetime:
        return datetime.datetime.now()


class Buffer:
    """Buffer ensures that there is no partial command at the end of the data
    chunk (that can happen if the data does not fit in the socket buffer or
    just cause). If that happens the partual command will be reconstructed the
    next time process_data is called.
    """

    def __init__(self) -> None:
        self._data = b''

    def process_data(self, received_data: bytes) -> Generator[bytes, None, None]:
        """Process the data received from the socket. Returns bytes.

        received_data: bytes.
        """
        self._data += received_data
        while True:
            if b'\r\n' not in self._data:
                break
            line, sep, self._data = self._data.partition(b'\r\n')
            yield line


@dataclass()
class IRCConfig:
    server: str
    port: int
    ssl: bool
    nick: str
    channels: list[IRCConfigChannel]
    cert: IRCConfigCert | None
    ignore: list[str]
    inactivity_monitor: bool


@dataclass()
class IRCConfigChannel:
    name: str
    password: str | None = None


@dataclass()
class IRCConfigCert:
    certfile: str
    keyfile: str


class IRC(BaseResponder[IRCConfig]):
    """Connects to an IRC server, sends and receives commands.

    Example module config:

        "botnet": {
            "irc": {
                "server": "irc.example.com",
                "port": 6697,
                "ssl": true,
                "nick": "my_bot",
                "channels": [
                    {
                        "name": "#my-channel",
                        "password": null
                    }
                ],
                "cert": {
                    "certfile": "/path/to/bot.crt",
                    "keyfile": "/path/to/bot.key"
                },
                "ignore": [
                    "some-other-bot!*@*",
                ],
                "inactivity_monitor": true
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'irc'
    config_class = IRCConfig

    socket_timeout_seconds = 5
    select_timeout_seconds = 1
    wait_before_reconnecting_seconds = 5

    def __init__(self, config: Config) -> None:
        super().__init__(config)

        self.soc: socket.socket | None = None
        self.sock_lock = threading.Lock()

        message_out.connect(self.on_message_out)
        self.restart_event = threading.Event()
        self.stop_event = threading.Event()
        self.t = threading.Thread(target=self.run)

    @command('channel_join')
    @only_admins()
    @parse_command([('name', 1), ('password', '?')])
    def admin_command_channel_join(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Joins a channel.

        Syntax: channel_join CHANNEL_NAME [CHANNEL_PASSWORD]
        """
        password = args['password'][0] if 'password' in args else None
        self.join(args['name'][0], password)

    @command('channel_part')
    @only_admins()
    @parse_command([('name', 1)])
    def admin_command_channel_part(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Parts a channel.

        Syntax: channel_part CHANNEL_NAME
        """
        self.part(args['name'][0])

    @command('ignore')
    @only_admins()
    @parse_command([('pattern', 1)])
    def admin_command_ignore(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Ignores a user. Pattern should be in the following form with
        asterisks used as wildcards: nick!user@host.

        Syntax: ignore PATTERN
        """
        def add_ignore_pattern(config: IRCConfig) -> None:
            pattern = args['pattern'][0]
            if pattern not in config.ignore:
                config.ignore.append(pattern)

        self.change_config(add_ignore_pattern)
        self.respond(msg, 'Done!')

    @command('unignore')
    @only_admins()
    @parse_command([('pattern', 1)])
    def admin_command_unignore(self, msg: IncomingPrivateMessage, auth: AuthContext, args: Args) -> None:
        """Unignores a user.

        Syntax: unignore PATTERN
        """
        def remove_ignore_pattern(config: IRCConfig) -> None:
            pattern = args['pattern'][0]
            if pattern in config.ignore:
                config.ignore.remove(pattern)

        self.change_config(remove_ignore_pattern)
        self.respond(msg, 'Done!')

    @command('ignored')
    @only_admins()
    def admin_command_ignored(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
        """Lists ignored patterns.

        Syntax: ignored
        """
        config = self.get_config()
        patterns_text = ', '.join(config.ignore) if len(config.ignore) > 0 else 'none'
        text = 'Ignored patterns: %s' % patterns_text
        self.respond(msg, text)

    @reply_handler(Code.RPL_ENDOFMOTD)
    def handler_rpl_endofmotd(self, msg: Message) -> None:
        self.join_from_config()

    @ping_message_handler()
    def handler_ping(self, ping: IncomingPing) -> None:
        pong = Message(command='PONG', params=ping.params)
        self.send(pong.to_string())

    def start(self) -> None:
        self.t.start()

    def stop(self) -> None:
        """To stop correctly it is necessary to disconnect from the server
        because blocking sockets are used.
        """
        super().stop()
        self.disconnect()
        self.stop_event.set()
        self.t.join()

    def restart(self) -> None:
        """Makes the module reconnect to the irc server."""
        self.disconnect()
        self.restart_event.set()

    def on_message_out(self, sender: Any, msg: Message) -> None:
        """Handler for the message_out signal.

        sender: object sending the signal, most likely another module.
        msg: Message object.
        """
        self.send(msg.to_string())

    def line_to_message(self, line: bytes) -> Message:
        """Converts a line received from the server to a message object.

        line: bytes.
        """
        line_str = line.decode()
        return Message.new_from_string(line_str)

    def process_data(self, buffer: Buffer, data: bytes) -> None:
        """Processes data received from the servers, partitions it into lines
        and passes each line to process_line.

        data: bytes.
        """
        for line in buffer.process_data(data):
            try:
                self.process_line(line)
            except Exception as e:
                on_exception.send(self, e=e)

    def process_line(self, line: bytes) -> None:
        """Process one line received from the server.

        line: bytes.
        """
        if not line:
            return
        msg = self.line_to_message(line)
        self.handle_message(msg)

    def handle_message(self, msg: Message) -> None:
        """Process the created Message object."""
        self.logger.debug('Received: %s', str(msg))

        # Check if the user should be ignored or not
        if self.should_ignore(msg):
            return

        # Forward the message to other modules
        try:
            message_in.send(self, msg=msg)
        except Exception as e:
            on_exception.send(self, e=e)

    def should_ignore(self, msg: Message) -> bool:
        if msg.prefix:
            config = self.get_config()
            for ignore_pattern in config.ignore:
                if fnmatch.fnmatch(msg.prefix, ignore_pattern):
                    return True
        return False

    def send(self, text: str) -> None:
        if len(text) == 0:
            self.logger.warning('Tried sending an empty message, not sending')
            return

        with self.sock_lock:
            if self.soc is None:
                self.logger.warning('Tried sending while socket is None, not sending')
                return

            try:
                self.logger.debug('Sending:  %s', text)
                full_text = '%s\r\n' % text
                data = full_text.encode('utf-8')
                self.soc.send(data)
            except (OSError, ssl.SSLError) as e:
                on_exception.send(self, e=e)

    def connect(self) -> None:
        """Initiates the connection."""
        with self.sock_lock:
            config = self.get_config()
            self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if config.ssl:
                context = ssl.create_default_context()
                if config.cert is not None:
                    context.load_cert_chain(certfile=config.cert.certfile, keyfile=config.cert.keyfile)
                self.soc = context.wrap_socket(self.soc, server_hostname=config.server)
            else:
                self.logger.warning('SSL disabled')
            self.soc.connect((config.server, config.port))
            self.soc.settimeout(self.socket_timeout_seconds)

    def disconnect(self) -> None:
        self.send('QUIT :Disconnecting')

    def identify(self) -> None:
        """Identifies with a server."""
        config = self.get_config()
        self.send('NICK ' + config.nick)
        self.send('USER botnet botnet botnet :Python bot')

    def join_from_config(self) -> None:
        """Joins all channels defined in the config."""
        config = self.get_config()
        for channel in config.channels:
            self.join(channel.name, channel.password)

    def join(self, channel_name: str, channel_password: str | None) -> None:
        msg = 'JOIN ' + channel_name
        if channel_password is not None:
            msg += ' ' + channel_password
        self.send(msg)

    def part(self, channel_name: str) -> None:
        msg = 'PART ' + channel_name
        self.send(msg)

    def get_inactivity_monitor(self) -> InactivityMonitor | NoopWith:
        config = self.get_config()
        if config.inactivity_monitor:
            self.logger.debug('InactivityMonitor is being used')
            return InactivityMonitor(self)
        else:
            self.logger.debug('InactivityMonitor is NOT being used')
            return NoopWith()

    def update(self) -> None:
        """Main method which should be called."""
        self.logger.debug('Update')
        with self.get_inactivity_monitor():
            try:
                self.restart_event.clear()
                self.connect()
                self.identify()
                self.receive_loop()
            finally:
                if self.soc:
                    self.soc.close()

    def receive_loop(self) -> None:
        buffer = Buffer()
        while not self.stop_event.is_set() and not self.restart_event.is_set():
            if self.soc is not None:
                reads, writes, errors = select.select([self.soc], [], [], self.select_timeout_seconds)
                for sock in reads:
                    if sock == self.soc:
                        data = self.soc.recv(4096)
                        if not data:
                            raise Exception('No data could be read')
                        self.process_data(buffer, data)

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.update()
            except Exception as e:
                on_exception.send(self, e=e)
                self.stop_event.wait(self.wait_before_reconnecting_seconds)


mod = IRC
