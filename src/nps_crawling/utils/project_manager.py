"""Module for managing project configurations and the active project state."""

import json
import subprocess
from pathlib import Path

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


def create_project(name: str, description: str) -> Path:
    """Creates a new project configuration JSON file in the projects directory.

    Args:
        name: Name of the project.
        description: Description of the project.

    Returns:
        The Path to the created project configuration file.
    """
    root_dir = get_git_root()
    projects_dir = root_dir / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    project_file = projects_dir / f"{name}.json"
    project_data = {
        "name": name,
        "description": description,
    }

    with open(project_file, "w", encoding="utf-8") as f:
        json.dump(project_data, f, indent=2, ensure_ascii=False)

    return project_file


def get_available_projects() -> list[str]:
    """Returns a list of all available project names in the projects directory."""
    root_dir = get_git_root()
    projects_dir = root_dir / "projects"
    if not projects_dir.exists():
        return []
    return [f.stem for f in projects_dir.glob("*.json")]


def get_active_project() -> tuple[str, str] | None:
    """Returns the name and description of the active project, or None if no project is active."""
    root_dir = get_git_root()
    active_file = root_dir / ".active_project"
    if active_file.exists():
        name = active_file.read_text(encoding="utf-8").strip()
        project_file = root_dir / "projects" / f"{name}.json"
        if project_file.exists():
            try:
                with open(project_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("name"), data.get("description", "")
            except Exception:
                return name, ""
        return name, ""
    return None


def has_active_project() -> bool:
    """Returns True if a project is currently active, False otherwise."""
    return get_active_project() is not None


def has_active_projects() -> bool:
    """Alias for has_active_project."""
    return has_active_project()


def activate_project(name: str) -> None:
    """Sets the active project by writing its name to .active_project.

    Args:
        name: Name of the project to activate.
    """
    root_dir = get_git_root()
    projects_dir = root_dir / "projects"
    project_file = projects_dir / f"{name}.json"
    if not project_file.exists():
        raise FileNotFoundError(f"Project '{name}' does not exist in '{projects_dir}'.")

    active_file = root_dir / ".active_project"
    active_file.write_text(name, encoding="utf-8")


def deactivate_project() -> None:
    """Clears the active project by removing the .active_project file."""
    root_dir = get_git_root()
    active_file = root_dir / ".active_project"
    if active_file.exists():
        active_file.unlink()
