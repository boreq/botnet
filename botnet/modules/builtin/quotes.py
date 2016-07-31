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
        rw = super(Quotes, self).get_all_commands()
        try:
            for command in self.config['module_config'][self.config_namespace][self.config_name].keys():
                rw.append(command)
        except:
            pass
        return rw

    def handle_privmsg(self, msg):
        if self.is_command(msg):
            key = self.get_command_name(msg)

            # Directories
            for directory in self.config_get('directories', []):
                for root, dirs, files in os.walk(directory):
                    for filename in files:
                        if filename == key:
                            path = os.path.join(root, filename)
                            self.send_random_line(msg, path)
                            return

            # Files
            filename = self.config_get('files.%s' % key, None)
            if filename is not None:
                self.send_random_line(msg, filename)

    def send_random_line(self, msg, filepath):
        try:
            line = random_line(filepath)
            self.respond(msg, line)
        except FileNotFoundError as e:
            on_exception.send(self, e=e)


mod = Quotes
