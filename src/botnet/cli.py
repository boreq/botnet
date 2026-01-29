"""
    Command line interface, `cli` group serves as an entry point for the script
    called `botnet`.
"""


import logging
import signal
from datetime import datetime
from types import FrameType

import click

from .config import Config
from .manager import Manager
from .modules.builtin.vibecheck import Vibecheck
from .modules.lib.log import LogLoader

logger_levels = ['warning', 'info', 'debug']


@click.group()
@click.option('--verbosity', type=click.Choice(logger_levels), default='warning')
def cli(verbosity: str) -> None:
    """IRC bot written in Python."""
    log_format = '%(asctime)s %(levelname)s %(name)s: %(message)s'
    log_level = getattr(logging, verbosity.upper(), None)
    logging.basicConfig(format=log_format, level=log_level)


@cli.command()
@click.argument('config', type=click.Path(exists=True))
def run(config: str) -> None:
    """Runs the bot."""
    def signal_handler(signum: int, frame: FrameType | None) -> None:
        manager.stop()

    def attach_signals() -> None:
        for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
            signal.signal(sig, signal_handler)

    manager = Manager(config_path=config)
    attach_signals()
    manager.run()


@cli.command()
@click.argument('config', type=click.Path(exists=True))
@click.argument('log', type=click.Path(exists=True))
def initialize_data_from_logs(config: str, log: str) -> None:
    """Initializes module data from old logs."""

    cfg = Config()
    cfg.from_json_file(config)

    class GaslitVibecheck(Vibecheck):

        now_to_return: datetime | None = None

        def _now(self) -> datetime:
            if self.now_to_return is None:
                raise ValueError('now_to_return is not set')
            return self.now_to_return

    m = GaslitVibecheck(cfg)

    loader = LogLoader()
    for message_with_time in loader.iter(log):
        m.now_to_return = message_with_time.received_at

        if message_with_time.message.command == 'PRIVMSG':
            print(message_with_time.received_at, message_with_time.message)
            m.handler_privmsg(message_with_time.message)

        if message_with_time.message.command == 'KICK':
            print(message_with_time.received_at, message_with_time.message)
            m.handler_kick(message_with_time.message)

        if message_with_time.message.command == 'JOIN':
            print(message_with_time.received_at, message_with_time.message)
            m.handler_join(message_with_time.message)
