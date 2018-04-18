import threading
import os
from ...signals import on_exception
from .. import BaseResponder
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

    def __init__(self, config):
        super(Markov, self).__init__(config)
        self.cache = {}
        t = threading.Thread(target=self.cache_chains, daemon=True)
        t.start()

    def get_all_commands(self):
        rw = super(Markov, self).get_all_commands()
        new_commands = set()
        for command in self.config_get('files', {}).keys():
            new_commands.add(command)
        for root, filename in self.get_command_files():
            new_commands.add(filename)
        rw.extend(new_commands)
        return rw

    def handle_privmsg(self, msg):
        if self.is_command(msg):
            key = self.get_command_name(msg)
            self.send_random_line(msg, key)

    def get_command_files(self):
        for directory in self.config_get('directories', []):
            for root, dirs, files in os.walk(directory, followlinks=True):
                for filename in files:
                    yield (root, filename)

    def cache_chains(self):
        # Directories
        for root, filename in self.get_command_files():
            path = os.path.join(root, filename)
            self.load_chain(path, filename)

        # Files
        for filename, path in self.config_get('files', {}).items():
            self.load_chain(path, filename)

    def load_chain(self, filepath, key):
        print(filepath, key)
        c = Chain()
        with open(filepath) as f:
            for line in f:
                c.grow(line.split())
        self.cache[key] = c

    def send_random_line(self, msg, key):
        try:
            c = self.cache[key]
            if c is not None:
                words = c.generate()
                line = ' '.join(words)
                self.respond(msg, line)
        except FileNotFoundError as e:
            on_exception.send(self, e=e)


mod = Markov
