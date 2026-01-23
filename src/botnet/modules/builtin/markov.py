import threading
import os
from typing import Iterator
from ...signals import on_exception
from .. import BaseResponder, AuthContext
from ...config import Config
from ...message import IncomingPrivateMessage
from markov import Chain


class Markov(BaseResponder):
    """Generates random responses using Markov chains from the files defined in
    config. This module will discover the files automatically by name if a
    directory containing them is included in the config.

    Warning: the files should contain each sentence in a separate line!

    Example module config:

        "botnet": {
            "markov": {
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
    config_name = 'markov'

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.cache: dict[str, Chain] = {}
        t = threading.Thread(target=self.cache_chains, daemon=True)
        t.start()

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

        self.send_random_line(msg, command_name)

    def get_command_files(self) -> Iterator[tuple[str, str]]:
        for directory in self.config_get('directories', []):
            for root, dirs, files in os.walk(directory, followlinks=True):
                for filename in files:
                    yield (root, filename)

    def cache_chains(self) -> None:
        # Directories
        for root, filename in self.get_command_files():
            path = os.path.join(root, filename)
            self.load_chain(path, filename)

        # Files
        for filename, path in self.config_get('files', {}).items():
            self.load_chain(path, filename)

    def load_chain(self, filepath: str, key: str) -> None:
        c = Chain()
        with open(filepath) as f:
            for line in f:
                c.grow(line.split())
        self.cache[key] = c

    def send_random_line(self, msg: IncomingPrivateMessage, key: str) -> None:
        try:
            c = self.cache.get(key, None)
            if c is not None:
                words = c.generate()
                line = ' '.join(words)
                self.respond(msg, line)
        except FileNotFoundError as e:
            on_exception.send(self, e=e)


mod = Markov
