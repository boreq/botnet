import click
import logging
from .manager import Manager


logger = logging.getLogger('cli')
logger_levels = ['warning', 'info', 'debug']


@click.group()
@click.option('--verbosity', type=click.Choice(logger_levels), default='warning')
@click.pass_context
def cli(ctx, verbosity):
    log_format = '%(asctime)s %(levelname)s %(name)s: %(message)s'
    log_level = getattr(logging, verbosity.upper(), None)
    logging.basicConfig(format=log_format, level=log_level)


@cli.command()
@click.argument('config', type=click.Path(exists=True))
@click.pass_context
def run(ctx, config):
    manager = Manager(config_path=config)
    manager.run()
