"""Module for managing project configurations and the active project state."""

import json
import subprocess
from pathlib import Path

from nps_crawling.project_config import default_project_data, ensure_config_tree


def get_git_root() -> Path:
    """Return the root directory of the current Git repository."""
    try:
        return Path(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                text=True,
            ).strip(),
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(
            "Git-Root konnte nicht ermittelt werden. "
            "Stelle sicher, dass Git installiert ist und das Projekt "
            "innerhalb eines Git-Repositories liegt.",
        ) from exc


def projects_dir() -> Path:
    return get_git_root() / "projects"


def active_project_marker() -> Path:
    return get_git_root() / ".active_project"


def create_project(name: str, description: str = "") -> Path:
    """Creates a new project configuration JSON file with default pipeline settings."""
    root = get_git_root()
    ensure_config_tree(root)
    projects_root = projects_dir()
    projects_root.mkdir(parents=True, exist_ok=True)

    project_file = projects_root / f"{name}.json"
    project_data = default_project_data(name, description)

    with open(project_file, "w", encoding="utf-8") as f:
        json.dump(project_data, f, indent=2, ensure_ascii=False)

    return project_file


def get_available_projects() -> list[str]:
    """Returns a list of all available project names in the projects directory."""
    root = projects_dir()
    if not root.exists():
        return []
    return sorted(f.stem for f in root.glob("*.json"))


def get_active_project_name() -> str | None:
    """Return the active project name, or None if no project is active."""
    marker = active_project_marker()
    if not marker.exists():
        return None
    name = marker.read_text(encoding="utf-8").strip()
    return name or None


def get_active_project() -> tuple[str, str] | None:
    """Returns the name and description of the active project, or None."""
    name = get_active_project_name()
    if not name:
        return None

    project_file = projects_dir() / f"{name}.json"
    if project_file.exists():
        try:
            with open(project_file, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("name", name), data.get("description", "")
        except Exception:
            return name, ""
    return name, ""


def has_active_project() -> bool:
    """Returns True if a project is currently active, False otherwise."""
    return get_active_project_name() is not None


def has_active_projects() -> bool:
    """Alias for has_active_project."""
    return has_active_project()


def activate_project(name: str) -> None:
    """Sets the active project by writing its name to .active_project."""
    project_file = projects_dir() / f"{name}.json"
    if not project_file.exists():
        raise FileNotFoundError(f"Project '{name}' does not exist in '{projects_dir()}'.")

    active_project_marker().write_text(name, encoding="utf-8")


def deactivate_project() -> None:
    """Clears the active project by removing the .active_project file."""
    marker = active_project_marker()
    if marker.exists():
        marker.unlink()
