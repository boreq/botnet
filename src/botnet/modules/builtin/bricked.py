from .. import BaseResponder, AuthContext
from ...message import Message
from ..lib import get_url


class Bricked(BaseResponder):
    """Reports statuses.

    Example module config:

        "botnet": {
            "bricked": {
                "statuses": [
                    {
                        "commands": ["status"],
                        "channels": ["#channel"],
                        "instance": "https://example.com",
                        "id": "person_id"
                    }
                ]
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'bricked'

    def get_all_commands(self, msg: Message, auth: AuthContext) -> list[str]:
        rw = super().get_all_commands(msg, auth)
        new_commands = set()
        for entry in self.config_get('statuses', []):
            if msg.params[0] in entry['channels']:
                for command in entry['commands']:
                    new_commands.add(command)
        rw.extend(new_commands)
        return rw

    def handle_privmsg(self, msg: Message) -> None:
        command_name = self.get_command_name(msg)

        if command_name is None:
            return

        for entry in self.config_get('statuses', []):
            if command_name not in entry['commands']:
                continue

            if msg.params[0] not in entry['channels']:
                continue

            url = entry['instance'].rstrip('/') + '/api/status/' + entry['id']
            r = get_url(url)
            r.raise_for_status()
            j = r.json()
            self.respond(msg, '{:.0f}%'.format(j['status'] * 100))


mod = Bricked
