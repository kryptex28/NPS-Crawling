from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from typing_extensions import Self

from nps_crawling.config import Config
from nps_crawling.db.db_adapter import DbAdapter
from nps_crawling.utils.project_manager import get_git_root
from nps_crawling.project_config import active_project_file


class PreprocessingModel():
    instance = None

    def __new__(cls) -> Self:
        """Create or return the singleton instance of PreprocessingModel."""
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        """Initialize the PreprocessingModel instance."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._preprocessing = None

    @property
    def preprocessing(self) -> Any:
        """Lazy load and return the PreprocessingPipeline instance."""
        if self._preprocessing is None:
            from nps_crawling.preprocessing.utils import PreProcessingPipeline
            self._preprocessing = PreProcessingPipeline()
        return self._preprocessing

    def run_preprocessing(self) -> None:
        """Run the preprocessing pipeline workflow."""
        DbAdapter().ensure_table_exists()

        Config.reload_config()
        self._preprocessing = None
        self.preprocessing.pre_processing_workflow()

    def get_config_path(self) -> Path:
        """Retrieve the path to the preprocessing configuration file."""
        root = get_git_root()
        try:
            proj_file = active_project_file(root)
            if proj_file and proj_file.is_file():
                with open(proj_file, "r", encoding="utf-8") as f:
                    proj_data = json.load(f)
                prep_ref = proj_data.get("preprocess")
                from nps_crawling.project_config import section_config_path
                return section_config_path(prep_ref, "preprocess", root)
        except Exception:
            pass
        from nps_crawling.project_config import CONFIG_TREE_PATHS
        return root / CONFIG_TREE_PATHS["preprocess"]

    def get_config(self) -> dict[str, Any]:
        """Load and return the preprocessing configuration dictionary."""
        path = self.get_config_path()
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_config(self, updates: dict[str, Any]) -> None:
        """Save updates to the preprocessing configuration file."""
        root = get_git_root()
        from nps_crawling.project_config import save_project_section
        try:
            save_project_section("preprocess", updates, root)
        except Exception:
            # Fallback if no active project is loaded
            path = self.get_config_path()
            config_data = self.get_config()
            config_data.update(updates)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

        Config.reload_config()