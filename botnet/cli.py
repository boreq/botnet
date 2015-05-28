"""
    Command line interface, `cli` group serves as an entry point for the script
    called `botnet`.
"""


import click
import logging
import signal
from .manager import Manager
from .modules import get_module


logger_levels = ['warning', 'info', 'debug']


@click.group()
@click.option('--verbosity', type=click.Choice(logger_levels), default='warning')
@click.pass_context
def cli(ctx, verbosity):
    """IRC bot written in Python."""
    log_format = '%(asctime)s %(levelname)s %(name)s: %(message)s'
    log_level = getattr(logging, verbosity.upper(), None)
    logging.basicConfig(format=log_format, level=log_level)


@cli.command()
@click.argument('config', type=click.Path(exists=True))
def run(config):
    """Runs the bot."""
    def signal_handler(signum, frame):
        manager.stop()

    def attach_signals():
        for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
            signal.signal(sig, signal_handler)

    manager = Manager(config_path=config)
    attach_signals()
    manager.run()
