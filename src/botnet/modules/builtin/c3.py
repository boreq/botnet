import datetime
from .. import BaseResponder, command, AuthContext
from ...message import IncomingPrivateMessage


class C3(BaseResponder):
    """Defines functions related to Chaos Communication Congress."""

    FIRST_CONGRESS_YEAR = 1984
    CONGRESS_MONTH = 12
    CONGRESS_DAY = 27

    @command('c3')
    def command_c3(self, msg: IncomingPrivateMessage, auth: AuthContext) -> None:
        """Displays the number of days remaining to the next congress.

        Syntax: c3
        """
        now = self.now()
        congress = datetime.datetime(year=now.year,
                                     month=self.CONGRESS_MONTH,
                                     day=self.CONGRESS_DAY)
        if congress < now:
            congress = congress.replace(year=congress.year + 1)

        number = congress.year - self.FIRST_CONGRESS_YEAR + 1
        if number > 36:
            number = number - 3
        days = (congress - now).days

        text = 'Time to {number}C3: {days} days'.format(number=number, days=days)
        self.respond(msg, text)

    def now(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.timezone.utc)


mod = C3
