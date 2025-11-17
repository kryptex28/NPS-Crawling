"""Command line interface."""

import argparse
import logging
import sys

from . import __version__

log = logging.getLogger(__package__)


def main(argv=None):
    """Parse arguments and execute commands."""
    args = create_parser().parse_args(argv)

    # Setup logger
    logging.basicConfig(
        format="{asctime} [{levelname:^8}] ({filename}:{lineno}) {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    )

    default_log_level = logging.WARNING
    verbosity = default_log_level - ((args.verbose - args.quiet) * 10)
    log_level = min(logging.CRITICAL, max(logging.DEBUG, verbosity))
    log.setLevel(log_level)

    try:
        log.info("Hello!")

    except Exception as error:
        if verbosity < default_log_level or default_log_level <= logging.DEBUG:
            log.exception(error)
        else:
            log.error(error)
            log.warning("Hint: Rerun with '--verbose' to show exception traceback.")
        sys.exit(1)
    except KeyboardInterrupt:
        log.warning("Aborted by user")
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-V",
        "--version",
        help="Show version number and exit",
        action="version",
        version=__version__,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        help="Increase output (Option is additive to increase verbosity)",
        action="count",
        default=0,
    )
    parser.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        help="Reduce output (Option is additive to decrease verbosity)",
        action="count",
        default=0,
    )
    return parser


if __name__ == "__main__":
    main()
