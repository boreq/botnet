import os
import random
from ...signals import on_exception
from .. import BaseResponder


def random_line(filename):
    """Gets a random line from file."""
    return random.choice(list(open(filename)))


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

    def get_all_commands(self):
        rw = super().get_all_commands()
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

            # Directories
            for root, filename in self.get_command_files():
                if filename == key:
                    path = os.path.join(root, filename)
                    self.send_random_line(msg, path)
                    return

            # Files
            filename = self.config_get('files.%s' % key, None)
            if filename is not None:
                self.send_random_line(msg, filename)

    def get_command_files(self):
        for directory in self.config_get('directories', []):
            for root, dirs, files in os.walk(directory, followlinks=True):
                for filename in files:
                    yield (root, filename)

    def send_random_line(self, msg, filepath):
        try:
            line = random_line(filepath)
            self.respond(msg, line)
        except FileNotFoundError as e:
            on_exception.send(self, e=e)


mod = Quotes
