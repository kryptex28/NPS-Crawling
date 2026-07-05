import json
from pathlib import Path
from typing_extensions import Self

from data_package.project_data import ProjectData
from nps_crawling.config import Config
from nps_crawling.utils.project_manager import (
    activate_project,
    get_available_projects,
    get_git_root,
    has_active_project,
    projects_dir,
)
from utils.pipeline_reset import reset_pipeline_models


class ProjectModel:

    instance = None

    def __new__(cls) -> Self:
        """Create or return the singleton instance of ProjectModel."""
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        """Initialize the ProjectModel instance."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self.categories: list[dict[str, str]] = []
            self.projects: list[ProjectData] = []

    def load_project(self, project_data: ProjectData) -> None:
        """Load the given project data, activate it, reload config, and reset other pipeline models."""
        activate_project(project_data.name)
        Config.reload_config()
        reset_pipeline_models()
        self.categories = list(Config.PROJECT_CATEGORIES)

    def create_config_file(self, ref: str, section: str) -> str:
        """Create a new default configuration file for a section (crawl/preprocess/classification)."""
        root = get_git_root()
        if not ref.strip():
            from nps_crawling.project_config import CONFIG_TREE_PATHS
            ref = CONFIG_TREE_PATHS[section]

        path = Path(ref.strip())
        if len(path.parts) == 1:
            name = path.stem
            ref_path = f"projects/configs/{section}/{name}.json"
            full_path = root / ref_path
        else:
            ref_path = str(path)
            full_path = root / path

        if full_path.is_file():
            raise FileExistsError(f"File already exists: {ref_path}")

        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        empty_templates = {
            "crawl": {
                "query_path": "",
                "sec_query_limit_count": 0,
                "download_delay": 0.0
            },
            "preprocess": {
                "version": "",
                "single_keyword_filter": None,
                "single_keyword_filter_strict": False,
                "threshold_keyword_scope": [],
                "threshold_keyword_scope_strict": False,
                "similarity_threshold_context_window": 0.0,
                "list_of_phrases_to_filter_filings_for": [],
                "list_of_phrases_to_exclude": [],
                "similarity_reference_text": "",
                "similarity_embedding_model": "",
                "amount_sentences_included_before": 0,
                "amount_sentences_included_after": 0,
                "max_context_chars_before_keyword": 0,
                "max_context_chars_after_keyword": 0,
                "files_per_chunk": 0
            },
            "classification": {
                "version": "",
                "random_seed": 0,
                "ground_truth_test_size": 0.0,
                "few_shot_num_examples": 0,
                "few_shot_text_column": "",
                "few_shot_sample_seed": 0,
                "config_use_name_files": False,
                "embedding_batch_size": 0,
                "llm_batch_size": 0,
                "classification_configuration": []
            }
        }
        
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(empty_templates[section], f, indent=2, ensure_ascii=False)

        return ref_path

    def _resolve_or_create_config(self, ref: str, section: str, root_dir: Path) -> str:
        """Resolve the path to a section's configuration file, creating a default one if it doesn't exist."""
        from nps_crawling.project_config import CONFIG_TREE_PATHS
        if not ref.strip():
            return CONFIG_TREE_PATHS[section]

        path = Path(ref.strip())
        if len(path.parts) == 1:
            name = path.stem
            ref_path = f"projects/configs/{section}/{name}.json"
            full_path = root_dir / ref_path
        else:
            ref_path = str(path)
            full_path = root_dir / path

        if not full_path.is_file():
            full_path.parent.mkdir(parents=True, exist_ok=True)
            empty_templates = {
                "crawl": {
                    "query_path": "",
                    "sec_query_limit_count": 0,
                    "download_delay": 0.0
                },
                "preprocess": {
                    "version": "",
                    "single_keyword_filter": None,
                    "single_keyword_filter_strict": False,
                    "threshold_keyword_scope": [],
                    "threshold_keyword_scope_strict": False,
                    "similarity_threshold_context_window": 0.0,
                    "list_of_phrases_to_filter_filings_for": [],
                    "list_of_phrases_to_exclude": [],
                    "similarity_reference_text": "",
                    "similarity_embedding_model": "",
                    "amount_sentences_included_before": 0,
                    "amount_sentences_included_after": 0,
                    "max_context_chars_before_keyword": 0,
                    "max_context_chars_after_keyword": 0,
                    "files_per_chunk": 0
                },
                "classification": {
                    "version": "",
                    "random_seed": 0,
                    "ground_truth_test_size": 0.0,
                    "few_shot_num_examples": 0,
                    "few_shot_text_column": "",
                    "few_shot_sample_seed": 0,
                    "config_use_name_files": False,
                    "embedding_batch_size": 0,
                    "llm_batch_size": 0,
                    "classification_configuration": []
                }
            }
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(empty_templates[section], f, indent=2, ensure_ascii=False)

        return ref_path

    def save_project(self, project_data: ProjectData) -> None:
        """Save the project configuration JSON file and activate it."""
        root = get_git_root()
        projects_root = projects_dir()
        projects_root.mkdir(parents=True, exist_ok=True)
        project_file = projects_root / f"{project_data.name}.json"

        crawl_path = self._resolve_or_create_config(
            project_data.crawl_config, "crawl", root
        )
        prep_path = self._resolve_or_create_config(
            project_data.preprocess_config, "preprocess", root
        )
        class_path = self._resolve_or_create_config(
            project_data.classification_config, "classification", root
        )

        data = {
            "name": project_data.name,
            "description": project_data.description,
            "crawl": crawl_path,
            "preprocess": prep_path,
            "classification": class_path,
        }

        with open(project_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        activate_project(project_data.name)
        Config.reload_config()
        reset_pipeline_models()
        self.categories = list(Config.PROJECT_CATEGORIES)

    def get_active_project(self) -> ProjectData | None:
        """Retrieve the currently active project metadata from the project config file."""
        from nps_crawling.utils.project_manager import get_active_project_name
        name = get_active_project_name()
        if not name:
            return None
        
        root = get_git_root()
        project_file = root / "projects" / f"{name}.json"
        
        description = ""
        crawl_config = ""
        preprocess_config = ""
        classification_config = ""
        
        if project_file.is_file():
            try:
                with open(project_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                description = data.get("description", "")
                crawl_config = data.get("crawl", "")
                preprocess_config = data.get("preprocess", "")
                classification_config = data.get("classification", "")
            except Exception:
                pass
                
        return ProjectData(
            id=1,
            name=name,
            description=description,
            crawl_config=crawl_config,
            preprocess_config=preprocess_config,
            classification_config=classification_config,
        )

    def get_projects(self) -> list[ProjectData]:
        """Scan the projects directory and return a list of all available projects."""
        self.projects.clear()
        projects_dir = get_git_root() / "projects"

        for name in get_available_projects():
            description = ""
            crawl_config = ""
            preprocess_config = ""
            classification_config = ""
            project_file = projects_dir / f"{name}.json"
            if project_file.is_file():
                try:
                    with open(project_file, encoding="utf-8") as f:
                        data = json.load(f)
                    description = data.get("description", "")
                    crawl_config = data.get("crawl", "")
                    preprocess_config = data.get("preprocess", "")
                    classification_config = data.get("classification", "")
                except Exception:
                    pass
            self.projects.append(
                ProjectData(
                    name=name,
                    id=1,
                    description=description,
                    crawl_config=crawl_config,
                    preprocess_config=preprocess_config,
                    classification_config=classification_config,
                )
            )

        return self.projects

    def add_category(self, category_name: str, category_type: str) -> None:
        """Add a search category to the project."""
        self.categories.append({"name": category_name, "type": category_type})

    def get_categories(self) -> list[dict[str, str]]:
        """Retrieve the search categories defined for the active project."""
        if not self.categories and Config.ACTIVE_PROJECT:
            self.categories = list(Config.PROJECT_CATEGORIES)
        return self.categories

    def is_project_active(self) -> bool:
        """Check if there is currently an active project loaded."""
        return has_active_project()

    def remove_category(self, category_name: str) -> None:
        """Remove a search category by name."""
        self.categories = [
            category for category in self.categories if category["name"] != category_name
        ]

    def clear_categories(self) -> None:
        """Clear all search categories."""
        self.categories.clear()
