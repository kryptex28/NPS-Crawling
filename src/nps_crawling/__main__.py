"""Command line interface."""

import argparse
import logging
import sys

from . import __version__

log = logging.getLogger(__package__)


def main(argv=None):
    """Parse arguments and execute commands."""
    parser = create_parser()
    args = parser.parse_args(argv)

    default_log_level = logging.WARNING
    verbosity = default_log_level - ((args.verbose - args.quiet) * 10)
    log_level = min(logging.INFO, max(logging.DEBUG, verbosity))
    log.setLevel(log_level)

    from nps_crawling.classification import ClassificationPipeline
    from nps_crawling.crawler import CrawlerPipeline
    from nps_crawling.preprocessing import PreProcessingPipeline
    from nps_crawling.results import ResultsPipeline

    try:
        if args.command == "crawl":
            crawler = CrawlerPipeline()
            crawler.crawler_workflow()
        elif args.command == "process":
            pre_processing = PreProcessingPipeline()
            pre_processing.pre_processing_workflow()
        elif args.command == "classify":
            classification = ClassificationPipeline()
            classification.classification_workflow()
        elif args.command == "display":
            results = ResultsPipeline()
            results.results_workflow()

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
    # Common arguments
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        help="Increase output (Option is additive to increase verbosity)",
        action="count",
        default=0,
    )
    parent.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        help="Reduce output (Option is additive to decrease verbosity)",
        action="count",
        default=0,
    )

    subparsers = parser.add_subparsers(
        dest="command",
    )

    subparsers.add_parser(
        "crawl",
        parents=[parent],
        description="Run crawler.",
    )
    subparsers.add_parser(
        "process",
        parents=[parent],
        description="Process data.",
    )
    subparsers.add_parser(
        "classify",
        parents=[parent],
        description="Classification of data.",
    )
    subparsers.add_parser(
        "display",
        parents=[parent],
        description="Displaying of Results.",
    )

    return parser


if __name__ == "__main__":
    main()
