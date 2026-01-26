import os
import threading
from dataclasses import dataclass
from typing import Iterator

from markov import Chain

from ...config import Config
from ...message import IncomingPrivateMessage
from ...signals import on_exception
from .. import AuthContext
from .. import BaseResponder


@dataclass()
class MarkovConfig:
    directories: list[str]
    files: dict[str, str]


class Markov(BaseResponder[MarkovConfig]):
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
    config_class = MarkovConfig

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.cache: dict[str, Chain] = {}
        t = threading.Thread(target=self.cache_chains, daemon=True)
        t.start()

    def get_all_commands(self, msg: IncomingPrivateMessage, auth: AuthContext) -> set[str]:
        rw = super().get_all_commands(msg, auth)
        config = self.get_config()
        for command in config.files.keys():
            rw.add(command)
        for root, filename in self._get_command_files(config):
            rw.add(filename)
        return rw

    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        command_name = self.get_command_name(msg)

        if command_name is None:
            return

        self.send_random_line(msg, command_name)

    def cache_chains(self) -> None:
        config = self.get_config()

        # Directories
        for root, filename in self._get_command_files(config):
            path = os.path.join(root, filename)
            self.load_chain(path, filename)

        # Files
        for filename, path in config.files.items():
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

    def _get_command_files(self, config: MarkovConfig) -> Iterator[tuple[str, str]]:
        for directory in config.directories:
            for root, dirs, files in os.walk(directory, followlinks=True):
                for filename in files:
                    yield (root, filename)


mod = Markov
