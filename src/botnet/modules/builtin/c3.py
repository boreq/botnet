import datetime
from dataclasses import dataclass

from ...message import IncomingPrivateMessage
from .. import AuthContext
from .. import BaseResponder
from .. import command


@dataclass()
class C3Config:
    pass


class C3(BaseResponder[C3Config]):
    """Defines functions related to Chaos Communication Congress."""

    config_namespace = 'botnet'
    config_name = 'c3'
    config_class = C3Config

    first_congress_year = 1984
    congress_month = 12
    congress_day = 27

    @command('c3')
    def command_c3(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
        """Displays the number of days remaining to the next congress.

        Syntax: c3
        """
        now = self._now()
        congress = datetime.datetime(year=now.year,
                                     month=self.congress_month,
                                     day=self.congress_day)
        if congress < now:
            congress = congress.replace(year=congress.year + 1)

        number = congress.year - self.first_congress_year + 1
        if number > 36:
            number = number - 3
        days = (congress - now).days

        text = 'Time to {number}C3: {days} days'.format(number=number, days=days)
        self.respond(msg, text)

    def _now(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.timezone.utc)


mod = C3
