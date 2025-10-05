from ...signals import message_out
from ...message import Message
from .. import BaseResponder
from ..lib import parse_command
from ...helpers import is_channel_name
from datetime import date, datetime


class Countdown(BaseResponder):
    """Allows you to define countdowns.

    Example module config:

        "botnet": {
            "countdown": {
                "summary_command": "summary",
                "commands": [
                    {
                        "names": ["ccc", "congress"],
                        "year": 2023,
                        "month": 8,
                        "day": 15
                    }
                ]
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'countdown'

    def __init__(self, config):
        super().__init__(config)

    def get_all_commands(self, msg_target):
        rw = super().get_all_commands(msg_target)
        new_commands = set()
        new_commands.add(self.config_get('summary_command'))
        for command in self.config_get('commands', []):
            new_commands.add(command['names'][0])
        rw.extend(new_commands)
        return rw

    def handle_privmsg(self, msg):
        if self.is_command(msg):
            key = self.get_command_name(msg)
            if key == self.config_get('summary_command'):
                responses = []
                for entry in self.config_get('commands', []):
                    time_left = self.generate_response(entry)
                    responses.append('{}: {}'.format(entry['names'][0], time_left))
                if len(responses) > 0:
                    self.respond(msg, ', '.join(responses))
            else:
                for entry in self.config_get('commands', []):
                    if key.lower() in [name.lower() for name in entry['names']]:
                        response = self.generate_response(entry) + '!'
                        self.respond(msg, response)
                        break

    def generate_response(self, target_date):
        year = int(target_date['year'])
        month = int(target_date['month'])
        day = int(target_date['day'])

        d0 = date(year, month, day)
        d1 = date.today()
        delta = d0 - d1
        if delta.days < 0:
            return 'It already happened'
        else:
            return '{} days left'.format(delta.days)


mod = Countdown
