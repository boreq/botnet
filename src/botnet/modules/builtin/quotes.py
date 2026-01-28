import os
import random
from dataclasses import dataclass
from typing import Iterator

from botnet.modules import privmsg_message_handler

from ...message import IncomingPrivateMessage
from ...signals import on_exception
from .. import AuthContext
from .. import BaseResponder


@dataclass()
class QuotesConfig:
    directories: list[str]
    files: dict[str, str]


class Quotes(BaseResponder[QuotesConfig]):
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
    config_class = QuotesConfig

    def get_all_commands(self, msg: IncomingPrivateMessage, auth: AuthContext) -> set[str]:
        rw = super().get_all_commands(msg, auth)
        config = self.get_config()
        for command in config.files.keys():
            rw.add(command)
        for root, filename in self._get_command_files(config):
            rw.add(filename)
        return rw

    @privmsg_message_handler()
    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        command_name = self.get_command_name(msg)

        if command_name is None:
            return

        config = self.get_config()

        # Directories
        for root, filename in self._get_command_files(config):
            if filename == command_name:
                path = os.path.join(root, filename)
                self._send_random_line(msg, path)
                return

        # Files
        foundfilename = config.files.get(command_name, None)
        if foundfilename is not None:
            self._send_random_line(msg, foundfilename)

    def _get_command_files(self, config: QuotesConfig) -> Iterator[tuple[str, str]]:
        for directory in config.directories:
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
