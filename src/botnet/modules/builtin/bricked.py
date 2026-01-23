from .. import BaseResponder, AuthContext
from ...message import IncomingPrivateMessage, Channel
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

    def get_all_commands(self, msg: IncomingPrivateMessage, auth: AuthContext) -> set[str]:
        rw = super().get_all_commands(msg, auth)
        channel = msg.target.channel
        if channel is not None:
            for entry in self.config_get('statuses', []):
                if channel in [Channel(str) for str in entry['channels']]:
                    for command in entry['commands']:
                        rw.add(command)
        return rw

    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        command_name = self.get_command_name(msg)
        if command_name is None:
            return

        channel = msg.target.channel
        if channel is not None:
            for entry in self.config_get('statuses', []):
                if command_name not in entry['commands']:
                    continue

                if channel.s.lower() not in entry['channels']:
                    continue

                url = entry['instance'].rstrip('/') + '/api/status/' + entry['id']
                r = get_url(url)
                r.raise_for_status()
                j = r.json()
                self.respond(msg, '{:.0f}%'.format(j['status'] * 100))


mod = Bricked
