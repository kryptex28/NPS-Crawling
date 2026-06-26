from typing_extensions import Self

from data_package.project_data import ProjectData

from nps_crawling.utils.project_manager import (
    activate_project,
    create_project,
    deactivate_project,
    get_active_project,
    get_available_projects,
    has_active_project,
    has_active_projects
)

class ProjectModel():

    instance = None

    def __new__(cls) -> Self:
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        if not hasattr(self, '_initialized'): 
            self._initialized = True
            self.categories: list[dict[str, str]] = []
            self.projects: list[ProjectData] = []
        pass

    def load_project(self, project_data: ProjectData) -> None:
        activate_project(project_data.name)

    def save_project(self, project_data: ProjectData) -> None:
        create_project(name=project_data.name, 
                       description=project_data.description)

    def get_projects(self) -> list[ProjectData]:
        self.projects.clear()
        
        for p in get_available_projects():
            self.projects.append(ProjectData(name=p,
                                            id=1,
                                            description=""))
            
        return self.projects
    
    def add_category(self, category_name: str, category_type: str) -> None:
        self.categories.append({"name": category_name, "type": category_type})
        
    def get_categories(self) -> list[dict[str, str]]:
        return self.categories
    
    def is_project_active(self) -> bool:
        return has_active_project()
    
    def remove_category(self, category_name: str) -> None:
        self.categories = [category for category in self.categories if category["name"] != category_name]
    
    def clear_categories(self) -> None:
        self.categories.clear()