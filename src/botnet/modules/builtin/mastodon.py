from .. import BaseResponder, AuthContext
from ...message import IncomingPrivateMessage, Channel
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

    max_toot_len = 250

    def get_all_commands(self, msg: IncomingPrivateMessage, auth: AuthContext) -> set[str]:
        rw = super().get_all_commands(msg, auth)
        channel = msg.target.channel
        if channel is not None:
            for entry in self.config_get('tooting', []):
                if channel in [Channel(string_channel) for string_channel in entry['channels']]:
                    rw.add(entry['command'])
        return rw

    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        command_name = self.get_command_name(msg)

        if command_name is None:
            return

        for entry in self.config_get('tooting', []):
            if entry['command'] != command_name:
                continue

            if msg.target not in entry['channels']:
                continue

            parts = msg.text.s.split(" ", 1)
            text = parts[1].strip()
            if len(text) > self.max_toot_len:
                return

            mastodon = MastodonLib(access_token=entry['access_token'], api_base_url=entry['instance'])
            toot = mastodon.toot(text)
            self.respond(msg, toot.url)


mod = Mastodon
