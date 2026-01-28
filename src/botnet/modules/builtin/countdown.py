from dataclasses import dataclass
from datetime import date

from botnet.modules import privmsg_message_handler

from ...config import Config
from ...message import IncomingPrivateMessage
from .. import AuthContext
from .. import BaseResponder


@dataclass()
class CountdownConfig:
    summary_command: str
    commands: list[CountdownConfigCommand]


@dataclass()
class CountdownConfigCommand:
    names: list[str]
    year: int
    month: int
    day: int

    def __post_init__(self) -> None:
        if len(self.names) == 0:
            raise ValueError('At least one command name must be specified')


class Countdown(BaseResponder[CountdownConfig]):
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
    config_class = CountdownConfig

    def __init__(self, config: Config) -> None:
        super().__init__(config)

    def get_all_commands(self, msg: IncomingPrivateMessage, auth: AuthContext) -> set[str]:
        rw = super().get_all_commands(msg, auth)
        config = self.get_config()
        rw.add(config.summary_command)
        for command in config.commands:
            rw.add(command.names[0])
        return rw

    @privmsg_message_handler()
    def handle_privmsg(self, msg: IncomingPrivateMessage) -> None:
        command_name = self.get_command_name(msg)

        if command_name is None:
            return

        config = self.get_config()

        if command_name == config.summary_command:
            responses = []
            for entry in config.commands:
                time_left = self._generate_response(entry)
                responses.append('{}: {}'.format(entry.names[0], time_left))
            if len(responses) > 0:
                self.respond(msg, ', '.join(responses))
        else:
            for entry in config.commands:
                if command_name.lower() in [name.lower() for name in entry.names]:
                    response = self._generate_response(entry) + '!'
                    self.respond(msg, response)
                    break

    def _generate_response(self, command: CountdownConfigCommand) -> str:
        year = int(command.year)
        month = int(command.month)
        day = int(command.day)

        d0 = date(year, month, day)
        d1 = self._now()
        delta = d0 - d1
        if delta.days < 0:
            return 'It already happened'
        else:
            return '{} days left'.format(delta.days)

    def _now(self) -> date:
        return date.today()


mod = Countdown
