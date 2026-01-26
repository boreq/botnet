"""
    Command line interface, `cli` group serves as an entry point for the script
    called `botnet`.
"""


import logging
import signal
from types import FrameType

import click

from .manager import Manager

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
