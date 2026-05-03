"""Utility script to ensure the Docker database container is running."""

import subprocess
import time

from nps_crawling.config import Config


def ensure_docker_db_running() -> None:
    """Startet den Docker-Postgres-Container wenn er noch nicht laeuft.

    Prueft zuerst via ``docker compose ps`` ob der Container bereits laeuft.
    Falls ja: kein Start, kein Warten - sofort weiter.
    Falls nein: ``docker compose up -d`` und kurz warten bis Postgres bereit ist.
    """
    if not Config.LOCAL_MODE:
        return

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

if __name__ == "__main__":
    ensure_docker_db_running()
