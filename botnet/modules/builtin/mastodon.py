from .. import BaseResponder
from mastodon import Mastodon as MastodonLib


class Mastodon(BaseResponder):
    """Let's you toot.

    Example module config:

        "botnet": {
            "mastodon": {
                "tooting": [
                    {
                        "command": "toot",
                        "channels": ["#channel"],
                        "instance": "https://example.com",
                        "access_token": "token"
                    }
                ]
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'mastodon'

    max_toot_len = 100

    def get_all_commands(self):
        rw = super().get_all_commands()
        new_commands = set()
        for entry in self.config_get('tooting', []):
            new_commands.add(entry['command'])
        rw.extend(new_commands)
        return rw

    def handle_privmsg(self, msg):
        if not self.is_command(msg):
            return

        command_name = self.get_command_name(msg)


        parts = msg.params[-1].split(" ", 1)
        text = parts[1].strip()
        if len(text) > self.max_toot_len:
            return

        for entry in self.config_get('tooting', []):
            if entry['command'] != command_name: 
                continue

            if msg.params[0] not in entry['channels']:
                continue

            mastodon = MastodonLib(access_token=entry['access_token'], api_base_url=entry['instance'])
            toot = mastodon.toot(text)
            self.respond(msg, toot.url)


mod = Mastodon
