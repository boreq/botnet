from botnet.config import Config
from botnet.modules.builtin.mumble import Mumble
from botnet.modules.builtin.mumble import mumble_pb2
from botnet.modules.builtin.mumble.mumble import encode, decode_header, \
    message_types, Decoder


def test_encode_decode():
    ver = mumble_pb2.Version()
    ver.version = 1
    ver.release = 'dev'
    ver.os = 'gnu'
    ver.os_version = 'linux'
    b = encode(ver)

    decoder = Decoder
    typ, length = decode_header(b[:6]) 
    assert message_types[typ] == type(ver)
    assert length


def test_decoder():
    ver = mumble_pb2.Version()
    ver.version = 1
    ver.release = 'dev'
    ver.os = 'gnu'
    ver.os_version = 'linux'
    b = encode(ver)

    def tester(msg):
        assert msg.version == 1
        assert msg.relase == 'dev'
        assert msg.os == 'gnu'
        assert msg.os_version == 'linux'

    decoder = Decoder(tester)
    decoder.write(b)
