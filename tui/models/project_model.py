from typing_extensions import Self

from data_package.project_data import ProjectData

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
        pass

    def load_project(self, project_id: str) -> None:
        pass

    def save_project(self, project_name: str, project_description: str) -> None:
        pass

    def get_projects(self) -> list[ProjectData]:
        return []
    
    def add_category(self, category_name: str, category_type: str) -> None:
        self.categories.append({"name": category_name, "type": category_type})
        
    def get_categories(self) -> list[dict[str, str]]:
        return self.categories
    
    def remove_category(self, category_name: str) -> None:
        self.categories = [category for category in self.categories if category["name"] != category_name]
    
    def clear_categories(self) -> None:
        self.categories.clear()