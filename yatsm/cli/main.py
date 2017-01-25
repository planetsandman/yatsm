""" Loads all commands for YATSM command line interface

Modeled after very nice `click` interface for `rasterio`:
https://github.com/mapbox/rasterio/blob/master/rasterio/rio/main.py

"""
import copy
import logging
import os
from pkg_resources import iter_entry_points
import sys

import click
import click_plugins
import cligj


# Configure logging
DEFAULT_LOG_FORMAT = ('%(asctime)s %(levelname)s %(name)s '
                       '%(module)s.%(funcName)s:%(lineno)s '
                       '%(message)s')
DEFAULT_LOG_TIME_FORMAT = '%H:%M:%S'


class ColorFormatter(logging.Formatter):
    colors = {
        'debug': dict(fg='blue'),
        'info': dict(fg='green'),
        'warning': dict(fg='yellow', bold=True),
        'error': dict(fg='red', bold=True),
        'exception': dict(fg='red', bold=True),
        'critical': dict(fg='red', bold=True)
    }

    def format(self, record):
        if not record.exc_info:
            record = copy.copy(record)
            style = self.colors.get(record.levelname.lower(), {})
            record.levelname = click.style(record.levelname, **style)
        return logging.Formatter.format(self, record)


class ClickHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            click.echo(msg, err=True)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


def config_logging(level, config=None):
    if config:
        logging.config.dictConfig(config)
    else:
        handler = ClickHandler()
        formatter = ColorFormatter(DEFAULT_LOG_FORMAT,
                                   DEFAULT_LOG_TIME_FORMAT)
        handler.setFormatter(formatter)

        logger = logging.getLogger('yatsm')
        logger.addHandler(handler)
        logger.setLevel(level)

        logger_algo = logging.getLogger('yatsm.algo')
        logger_algo.addHandler(handler)
        logger_algo.setLevel(level + 10)

        if level <= logging.INFO:  # silence rasterio
            logging.getLogger('rasterio').setLevel(logging.INFO)


# NumPy linear algebra multithreading related variables
NP_THREAD_VARS = [
    'OPENBLAS_NUM_THREADS',
    'MKL_NUM_THREADS',
    'OPM_NUM_THREADS'
]


def _config_numpy():
    def _set_np_thread_vars(n):
        for envvar in NP_THREAD_VARS:
            if envvar in os.environ:
                logger.warning('Overriding %s with --num_threads=%i'
                               % (envvar, n))
            os.environ[envvar] = str(n)


    # If --num_threads set, parse it before click CLI interface so envvars are
    # set BEFORE numpy is imported
    if '--num_threads' in sys.argv:
        n_threads = sys.argv[sys.argv.index('--num_threads') + 1]
        try:
            n_threads = int(n_threads)
        except ValueError as e:
            raise click.BadParameter('Cannot parse <threads> to an integer '
                                     '(--num_threads=%s): %s' %
                                     (n_threads, e.message))
        else:
            _set_np_thread_vars(n_threads)
    else:
        # Default to 1
        _set_np_thread_vars(1)
_config_numpy()


# Resume YATSM imports after NumPy has been configured
import yatsm  # flake8: noqa
from . import options  # flake8: noqa

# YATSM CLI group
_context = dict(
    token_normalize_func=lambda x: x.lower(),
    help_option_names=['--help', '-h']
)


@click_plugins.with_plugins(ep for ep in
                            iter_entry_points('yatsm.cli'))
@click.group(help='YATSM command line interface', context_settings=_context)
@click.version_option(yatsm.__version__)
@click.option('--num_threads', metavar='<threads>', default=1, type=int,
              show_default=True, callback=options.valid_int_gt_zero,
              help='Number of threads for OPENBLAS/MKL/OMP used in NumPy')
@cligj.verbose_opt
@cligj.quiet_opt
@click.pass_context
def cli(ctx, num_threads, verbose, quiet):
    verbosity = verbose - quiet
    level = max(10, 30 - 10 * verbosity)
    config_logging(level, config=None)  # TODO: dictConfig file arg

