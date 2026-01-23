import os
import random
from typing import Iterator
from ...signals import on_exception
from ...message import IncomingPrivateMessage
from .. import BaseResponder, AuthContext


class Quotes(BaseResponder):
    """Sends random lines from the files defined in config. This module will
    discover the files automatically by name if a directory containing them
    is included in the config.

    Example module config:

        "botnet": {
            "quotes": {
                "directories": [
                    "path/to/directory/with/quote/files1",
                    "path/to/directory/with/quote/files2"
                ],
                "files": {
                    "command_name1": "filepath1",
                    "command_name2": "filepath2"
                }
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'quotes'

    def get_all_commands(self, msg: IncomingPrivateMessage, auth: AuthContext) -> set[str]:
        rw = super().get_all_commands(msg, auth)
        for command in self.config_get('files', {}).keys():
            rw.add(command)
        for root, filename in self.get_command_files():
            rw.add(filename)
        return rw

    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        command_name = self.get_command_name(msg)

        if command_name is None:
            return

        # Directories
        for root, filename in self.get_command_files():
            if filename == command_name:
                path = os.path.join(root, filename)
                self._send_random_line(msg, path)
                return

        # Files
        filename = self.config_get('files.%s' % command_name, None)
        if filename is not None:
            self._send_random_line(msg, filename)

    def get_command_files(self) -> Iterator[tuple[str, str]]:
        for directory in self.config_get('directories', []):
            for root, dirs, files in os.walk(directory, followlinks=True):
                for filename in files:
                    yield (root, filename)

    def _send_random_line(self, msg: IncomingPrivateMessage, filepath: str) -> None:
        try:
            line = self._random_line(filepath)
            self.respond(msg, line)
        except FileNotFoundError as e:
            on_exception.send(self, e=e)

    def _random_line(self, filename: str) -> str:
        with open(filename) as f:
            return random.choice(list(f))


mod = Quotes
