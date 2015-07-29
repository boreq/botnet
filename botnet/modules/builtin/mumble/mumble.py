import socket
import ssl
import threading
import time
import struct
from ....logging import get_logger
from ....message import Message
from ....signals import on_exception
from ... import BaseResponder
from . import mumble_pb2


message_types = {
    0:   mumble_pb2.Version,
    1:   mumble_pb2.UDPTunnel,
    2:   mumble_pb2.Authenticate,
    3:   mumble_pb2.Ping,
    4:   mumble_pb2.Reject,
    5:   mumble_pb2.ServerSync,
    6:   mumble_pb2.ChannelRemove,
    7:   mumble_pb2.ChannelState,
    8:   mumble_pb2.UserRemove,
    9:   mumble_pb2.UserState,
    10:  mumble_pb2.BanList,
    11:  mumble_pb2.TextMessage,
    12:  mumble_pb2.PermissionDenied,
    13:  mumble_pb2.ACL,
    14:  mumble_pb2.QueryUsers,
    15:  mumble_pb2.CryptSetup,
    16:  mumble_pb2.ContextActionModify,
    17:  mumble_pb2.ContextAction,
    18:  mumble_pb2.UserList,
    19:  mumble_pb2.VoiceTarget,
    20:  mumble_pb2.PermissionQuery,
    21:  mumble_pb2.CodecVersion,
    22:  mumble_pb2.UserStats,
    23:  mumble_pb2.RequestBlob,
    24:  mumble_pb2.ServerConfig,
    25:  mumble_pb2.SuggestConfig,
}

# Format used for struct.pack() when encoding the message header.
_header_format = '!hi'

# Length of the header proceeding each protobuf encoded message.
# https://mumble-protocol.readthedocs.org/en/latest/protocol_stack_tcp.html
_header_length = 6

def encode(msg):
    """Encodes a message in the mumble protocol format."""
    payload = msg.SerializeToString()
    header = struct.pack(_header_format, message_type_to_number(msg), len(payload))
    return header + payload

def decode_header(header):
    """Decodes a header encoded in the mumble protocol format. Header must be
    _header_length bytes long. Returns (message type, message length)."""
    data = struct.unpack(_header_format, header)
    return data


def message_type_to_number(msg):
    """Converts a type of the message to the number used to encode it in the
    protocol."""
    for key, value in message_types.items():
        if value == type(msg):
            return key
    raise ValueError


class CriticalProtocolError(Exception):
    pass


class Decoder(object):
    """Decoder for mumble protobuf. Use write() to add data. After enough data
    will have been gathered by the decoder on_message function will be called 
    with the received message struct. on_message must be set to a function with
    the following signature: void on_message(msg).
    """

    def __init__(self, on_message):
        self.buf = bytes()
        self.on_message = on_message
        self.lock = threading.Lock()
        self.logger = get_logger(self)

    def write(self, data):
        """If this function throws it means that most likely a critial and
        unrecoverable protocol error has occured and the whole connection should
        be terminated."""
        with self.lock:
            self.buf = self.buf + data
            self.logger.debug('Added %s bytes, buffer is at %s bytes', len(data), len(self.buf))
            try:
                self._process()
            except:
                raise CriticalProtocolError

    def _process(self):
        while True:
            # Abort if not enough data to read the header.
            if len(self.buf) < _header_length:
                return
            typ, length = decode_header(self.buf[:6])
            total_length = _header_length + length
            # Abort if not enough data to read the entire message.
            if len(self.buf) < total_length:
                return
            try:
                msg = message_types[typ]()
                msg.ParseFromString(self.buf[_header_length:total_length])
                self.on_message(msg)
            except Exception as e:
                on_exception.send(self, e=e)
            finally:
                # Trash data which was already used.
                self.buf = self.buf[total_length:]
                self.logger.debug('Dropped data, buffer now at %s', len(self.buf))


class Mumble(BaseResponder):
    """Connects to a Mumble server.

    Example module config:

        "botnet": {
            "mumble": {
                "server": "irc.example.com",
                "port": 6667,
                "nick": "my_bot",
                "password": "password"
            }
        }

    """

    deltatime = 5

    def __init__(self, config):
        super(Mumble, self).__init__(config)
        self.register_config('botnet', 'base_responder')
        self.register_config('botnet', 'mumble')
        self.soc = None
        self.restart_event = threading.Event()
        self.decoder = Decoder(self.on_message)

        self.users = {}

    def command_mumble(self, msg):
        """Lists users who are on mumble.

        Syntax: mumble
        """
        users = [v['name'] for k, v in self.users.items() if v['name']]
        text =  "Users currently on mumble: %s" % ', '.join(users)
        self.respond(msg, text)

    def start(self):
        self.stop_event = threading.Event()
        self.t = threading.Thread(target=self.run)
        self.t.start()

        self.hbeat = threading.Thread(target=self.heartbeat)
        self.hbeat.start()

    def stop(self):
        """To stop correctly it is necessary to disconnect from the server
        because blocking sockets are used.
        """
        super(Mumble, self).stop()
        self.disconnect()
        self.stop_event.set()
        self.t.join()

    def restart(self):
        """Makes the module reconnect to the irc server."""
        self.disconnect()
        self.restart_event.set()

    def disconnect(self):
        if self.soc is not None:
            self.soc.close()
            self.soc = None

    def process_data(self, data):
        """Process data received from the socket."""
        self.decoder.write(data)

    def on_message(self, msg):
        """Triggered by decoder.
        msg: Message object.
        """
        # Dispatch the message to the right handler
        handler_name = 'handler_%s' % msg.__class__.__name__
        func = getattr(self, handler_name, None)
        if func is not None:
            self.logger.debug('Dispatching to %s', handler_name)
            func(msg)

    def handler_UserState(self, msg):
        if hasattr(msg, 'session') and hasattr(msg, 'name'):
            if msg.name:
                self.users[msg.session] = {
                    'name': msg.name,
                }

    def handler_UserRemove(self, msg):
        if hasattr(msg, 'session'):
            if msg.session in self.users:
                self.users.pop(msg.session)


    def send(self, msg):
        """Sends a protobuf message via the socket."""
        # To be honest I have never seen an exception here
        try:
            if self.soc:
                data = encode(msg)
                self.logger.debug('Sending %s (%s bytes)', type(msg), len(data))
                self.logger.debug('\n%s', msg)
                self.soc.send(data)
                return True
        except (OSError, ssl.SSLError) as e:
            on_exception.send(self, e=e)
        return False

    def connect(self):
        """Initiates the connection."""
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.soc = ssl.wrap_socket(soc)
        self.soc.connect((self.config_get('server'), self.config_get('port')))
        self.soc.settimeout(1)

    def identify(self):
        ver = mumble_pb2.Version()
        ver.version = 1
        ver.release = 'dev'
        ver.os = 'gnu'
        ver.os_version = 'linux'
        self.send(ver)

        auth = mumble_pb2.Authenticate()
        auth.username = self.config_get('nick')
        auth.password = self.config_get('password', '')
        self.send(auth)

    def heartbeat(self):
        while not self.stop_event.is_set():
            try:
                self.logger.debug('Heartbeat')
                ping = mumble_pb2.Ping()
                self.send(ping)
                self.stop_event.wait(15)
            except:
                pass

    def update(self):
        """Main method which should be called."""
        self.logger.debug('Update')
        try:
            self.restart_event.clear()
            self.connect()
            self.identify()
            while not self.stop_event.is_set() and not self.restart_event.is_set():
                try:
                    data = self.soc.recv(4096)
                    if not data:
                        break
                    self.process_data(data)
                except CriticalProtocolError:
                    raise
                except (socket.timeout, ssl.SSLWantReadError) as e:
                    pass
            time.sleep(10)
        finally:
            if self.soc:
                self.soc.close()

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.update()
                self.stop_event.wait(self.deltatime)
            except:
                pass
