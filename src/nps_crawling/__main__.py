"""Command line interface."""

import argparse
import logging
import shutil
import subprocess
import sys

from nps_crawling.config import Config

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

    if Config.LOCAL_MODE:
        _ensure_docker_db_running()
        from nps_crawling.db.db_adapter import DbAdapter
        DbAdapter().ensure_table_exists()

    try:
        if args.command == "crawl":
            crawler = CrawlerPipeline()
            crawler.crawler_workflow()
        elif args.command == "process":
            # need to do check here, since otherwise huggingface weights would still be loaded
            processed_dir = Config.NPS_CONTEXT_JSON_PATH / "files"
            if processed_dir.exists() and any(processed_dir.glob("*.json")):
                print(
                    f"Experiment '{Config.PREPROCESSING_VERSION}' already has processed "
                    f"data at {processed_dir} — skipping preprocessing",
                )
            else:
                pre_processing = PreProcessingPipeline()
                pre_processing.pre_processing_workflow()
        elif args.command == "classify":

            classified_dir = Config.NPS_CLASSIFIED_JSON / "files"

            if args.force and Config.NPS_CLASSIFIED_JSON.exists():
                shutil.rmtree(Config.NPS_CLASSIFIED_JSON)
                Config.NPS_CLASSIFIED_JSON.mkdir(parents=True, exist_ok=True)
                classified_dir.mkdir(parents=True, exist_ok=True)

            if classified_dir.exists() and any(classified_dir.glob("*.json")):
                print(
                    f"Experiment '{Config.CLASSIFICATION_VERSION}' already has classified "
                    f"data at {classified_dir} — skipping classification",
                )
            else:
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
    classify_parser = subparsers.add_parser(
        "classify",
        parents=[parent],
        description="Classification of data.",
    )
    classify_parser.add_argument(
        "--force",
        action="store_true",
        help="Force classification by deleting existing classified data",
    )
    subparsers.add_parser(
        "display",
        parents=[parent],
        description="Displaying of Results.",
    )

    return parser


if __name__ == "__main__":
    main()


def _ensure_docker_db_running() -> None:
    """Startet den Docker-Postgres-Container wenn er noch nicht laeuft.

    Prueft zuerst via ``docker compose ps`` ob der Container bereits laeuft.
    Falls ja: kein Start, kein Warten - sofort weiter.
    Falls nein: ``docker compose up -d`` und kurz warten bis Postgres bereit ist.
    """
    import time

    compose_file = Config.ROOT_DIR / "docker" / "database" / "docker-compose.yml"

    # Pruefen ob der Container bereits laeuft
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "ps", "--services", "--filter", "status=running"],
            capture_output=True,
            text=True,
            check=True,
        )
        already_running = bool(result.stdout.strip())
    except FileNotFoundError:
        raise RuntimeError(
            "'docker' wurde nicht gefunden. Bitte Docker Desktop installieren und starten.",
        ) from None
    except subprocess.CalledProcessError:
        already_running = False

    if already_running:
        print("Docker-Postgres laeuft bereits.", flush=True)
        return

    # Container starten
    print("LOCAL_MODE aktiv - starte Docker-Postgres...", flush=True)
    try:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d"],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"'docker compose up -d' ist fehlgeschlagen (Exit-Code {exc.returncode}). "
            "Bitte Docker Desktop starten und erneut versuchen.",
        ) from exc

    # Kurz warten, bis Postgres vollstaendig hochgefahren ist
    time.sleep(3)
    print("Docker-Postgres laeuft.", flush=True)
