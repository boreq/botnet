from .. import BaseResponder
from ..lib import get_url


class Bricked(BaseResponder):
    """Reports statuses.

    Example module config:

        "botnet": {
            "bricked": {
                "statuses": [
                    {
                        "command": "status",
                        "channels": ["#channel"],
                        "instance": "https://example.com"
                    }
                ]
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'bricked'

    def get_all_commands(self):
        rw = super().get_all_commands()
        new_commands = set()
        for entry in self.config_get('statuses', []):
            new_commands.add(entry['command'])
        rw.extend(new_commands)
        return rw

    def handle_privmsg(self, msg):
        if not self.is_command(msg):
            return

        command_name = self.get_command_name(msg)

        for entry in self.config_get('statuses', []):
            if entry['command'] != command_name: 
                continue

            if msg.params[0] not in entry['channels']:
                continue

            url = entry['instance'].rstrip('/') + '/api/status'
            r = get_url(url)
            r.raise_for_status()
            j = r.json()
            self.respond(msg, '{:.0f}%'.format(j['status'] * 100))


mod = Bricked
