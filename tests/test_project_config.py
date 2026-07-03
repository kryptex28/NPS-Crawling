import json

import pytest

from nps_crawling.config import Config
from nps_crawling.project_config import (
    DEFAULT_PROJECT_CONFIG,
    default_project_data,
    ensure_config_tree,
    load_project_file,
)
from nps_crawling.utils import project_manager


def test_default_project_data_contains_all_sections():
    data = default_project_data("example", "desc")
    assert data["name"] == "example"
    assert data["description"] == "desc"
    assert set(data) >= {"crawl", "preprocess", "classification"}
    assert isinstance(data["crawl"], str)
    assert isinstance(data["preprocess"], str)
    assert isinstance(data["classification"], str)


def test_load_project_file_resolves_config_tree(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    configs_root = tmp_path / "projects" / "configs"
    (configs_root / "crawl").mkdir(parents=True)
    (configs_root / "preprocess").mkdir(parents=True)
    (configs_root / "classification").mkdir(parents=True)
    (configs_root / "crawl" / "default.json").write_text(
        json.dumps({"query_path": "custom_query", "sec_query_limit_count": 5, "download_delay": 0.1}),
        encoding="utf-8",
    )
    (configs_root / "preprocess" / "version_2.json").write_text(
        json.dumps({"version": "custom_preprocess"}),
        encoding="utf-8",
    )
    (configs_root / "classification" / "version_1.json").write_text(
        json.dumps(
            {
                "version": "custom_classification",
                "classification_configuration": [],
            }
        ),
        encoding="utf-8",
    )

    project_file = tmp_path / "projects" / "tree_project.json"
    project_file.write_text(
        json.dumps(
            {
                "name": "tree_project",
                "crawl": "projects/configs/crawl/default.json",
                "preprocess": "projects/configs/preprocess/version_2.json",
                "classification": "projects/configs/classification/version_1.json",
            }
        ),
        encoding="utf-8",
    )

    data = load_project_file(project_file, root_dir=tmp_path)
    assert data["crawl"]["query_path"] == "custom_query"
    assert data["preprocess"]["version"] == "custom_preprocess"
    assert data["classification"]["version"] == "custom_classification"


def test_load_project_file_merges_partial_config(tmp_path):
    project_file = tmp_path / "partial.json"
    project_file.write_text(
        json.dumps(
            {
                "name": "partial",
                "preprocess": {"version": "custom_v"},
            }
        ),
        encoding="utf-8",
    )

    data = load_project_file(project_file, root_dir=tmp_path)
    assert data["name"] == "partial"
    assert data["preprocess"]["version"] == "custom_v"
    assert data["crawl"]["query_path"] == DEFAULT_PROJECT_CONFIG["crawl"]["query_path"]


def test_apply_project_file_updates_config(tmp_path, monkeypatch):
    monkeypatch.setattr(project_manager, "get_git_root", lambda: tmp_path)
    ensure_config_tree(tmp_path)

    project_file = project_manager.create_project("cfg_test", "Config test project")
    Config.apply_project_file(project_file)

    assert Config.ACTIVE_PROJECT == "cfg_test"
    assert Config.PREPROCESSING_VERSION == DEFAULT_PROJECT_CONFIG["preprocess"]["version"]
    assert Config.CLASSIFICATION_VERSION == DEFAULT_PROJECT_CONFIG["classification"]["version"]
    assert len(Config.CLASSIFICATION_CONFIGURATION) > 0
    assert Config.RAW_JSON_PATH_CRAWLER == Config.DATA_PATH / "cfg_test" / "json_raw"
    assert len(Config.PROJECT_CATEGORIES) > 0


def test_reload_config_without_active_project(monkeypatch, tmp_path):
    monkeypatch.setattr(project_manager, "get_git_root", lambda: tmp_path)
    marker = tmp_path / ".active_project"
    if marker.exists():
        marker.unlink()

    Config.reload_config()
    assert Config.ACTIVE_PROJECT is None
    assert Config.DATABASE_TABLE_NAME == "default"
