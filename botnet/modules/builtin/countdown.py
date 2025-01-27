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
                "commands": {
                    "camp": {
                        "year": 2023,
                        "month": 8,
                        "day": 15
                    }
                }
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'countdown'

    def __init__(self, config):
        super().__init__(config)

    def handle_privmsg(self, msg):
        if self.is_command(msg):
            key = self.get_command_name(msg)
            if key == self.config_get('summary_command'):
                responses = []
                for name, date in self.config_get('commands', {}).items():
                    time_left = self.generate_response(date)
                    responses.append('{}: {}'.format(name, time_left))
                if len(responses) > 0:
                    self.respond(msg, ', '.join(responses))
            else:
                target_date = self.config_get('commands').get(key, None)
                if target_date is not None:
                    response = self.generate_response(target_date) + '!'
                    self.respond(msg, response)

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
