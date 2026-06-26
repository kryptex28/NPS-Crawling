import json
from typing_extensions import Self

from data_package.project_data import ProjectData
from nps_crawling.config import Config
from nps_crawling.utils.project_manager import (
    activate_project,
    create_project,
    get_active_project,
    get_available_projects,
    get_git_root,
    has_active_project,
)
from utils.pipeline_reset import reset_pipeline_models


class ProjectModel:

    instance = None

    def __new__(cls) -> Self:
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self.categories: list[dict[str, str]] = []
            self.projects: list[ProjectData] = []

    def load_project(self, project_data: ProjectData) -> None:
        activate_project(project_data.name)
        Config.reload_config()
        reset_pipeline_models()
        self.categories = list(Config.PROJECT_CATEGORIES)

    def save_project(self, project_data: ProjectData) -> None:
        create_project(name=project_data.name, description=project_data.description)
        activate_project(project_data.name)
        Config.reload_config()
        reset_pipeline_models()
        self.categories = list(Config.PROJECT_CATEGORIES)

    def get_active_project(self) -> ProjectData | None:
        active = get_active_project()
        if not active:
            return None
        return ProjectData(name=active[0], description=active[1], id=1)

    def get_projects(self) -> list[ProjectData]:
        self.projects.clear()
        projects_dir = get_git_root() / "projects"

        for name in get_available_projects():
            description = ""
            project_file = projects_dir / f"{name}.json"
            if project_file.is_file():
                try:
                    with open(project_file, encoding="utf-8") as f:
                        description = json.load(f).get("description", "")
                except Exception:
                    pass
            self.projects.append(ProjectData(name=name, id=1, description=description))

        return self.projects

    def add_category(self, category_name: str, category_type: str) -> None:
        self.categories.append({"name": category_name, "type": category_type})

    def get_categories(self) -> list[dict[str, str]]:
        if not self.categories and Config.ACTIVE_PROJECT:
            self.categories = list(Config.PROJECT_CATEGORIES)
        return self.categories

    def is_project_active(self) -> bool:
        return has_active_project()

    def remove_category(self, category_name: str) -> None:
        self.categories = [
            category for category in self.categories if category["name"] != category_name
        ]

    def clear_categories(self) -> None:
        self.categories.clear()
