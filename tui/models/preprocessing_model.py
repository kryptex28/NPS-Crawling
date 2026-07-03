from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from typing_extensions import Self

from nps_crawling.config import Config
from nps_crawling.preprocessing.utils import PreProcessingPipeline
from nps_crawling.db.db_adapter import DbAdapter
from nps_crawling.utils.project_manager import get_git_root
from nps_crawling.project_config import active_project_file, resolve_project_config_path


class PreprocessingModel():
    instance = None

    def __new__(cls) -> Self:
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._preprocessing: PreProcessingPipeline | None = None

    @property
    def preprocessing(self) -> PreProcessingPipeline:
        if self._preprocessing is None:
            self._preprocessing = PreProcessingPipeline()
        return self._preprocessing

    def run_preprocessing(self) -> None:
        DbAdapter().ensure_table_exists()

        Config.reload_config()
        self._preprocessing = None
        self.preprocessing.pre_processing_workflow()

    def get_config_path(self) -> Path:
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
        path = self.get_config_path()
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_config(self, updates: dict[str, Any]) -> None:
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