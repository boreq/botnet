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
            targetDate = self.config_get('commands').get(key, None)
            if targetDate is not None:
                year = int(targetDate['year'])
                month = int(targetDate['month'])
                day = int(targetDate['day'])

                d0 = date(year, month, day)
                d1 = date.today()
                delta = d0 - d1
                if delta.days < 0:
                    response = 'It already happened!'
                else:
                    response = '{} days left!'.format(delta.days)
                self.respond(msg, response)


mod = Countdown
