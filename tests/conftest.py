from botnet.message import Message
from botnet.signals import message_out
import logging
import os
import pytest
import tempfile


log_format = '%(asctime)s %(levelname)s %(name)s: %(message)s'
log_level = logging.DEBUG
logging.basicConfig(format=log_format, level=log_level)


@pytest.fixture()
def tmp_file(request):
    fd, path = tempfile.mkstemp()
    def teardown():
        os.close(fd)
        os.remove(path)
    request.addfinalizer(teardown)
    return path


@pytest.fixture()
def msg_t():
    class Trap(object):
        """Saves the last message sent via message_out signal."""

        def __init__(self):
            self.msg = None
            message_out.connect(self.on_message_out)

        def on_message_out(self, sender, msg):
            self.msg = msg

        def reset(self):
            self.msg = None

    return Trap()
