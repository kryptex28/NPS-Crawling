import json
from pathlib import Path
import pytest
from nps_crawling.utils import project_manager

def test_project_manager_workflow(tmp_path, monkeypatch):
    # Mock get_git_root to return our temporary path
    monkeypatch.setattr(project_manager, "get_git_root", lambda: tmp_path)

    # 1. Initially no projects, and active project is None
    assert project_manager.get_available_projects() == []
    assert project_manager.get_active_project() is None
    assert project_manager.has_active_project() is False
    assert project_manager.has_active_projects() is False

    # 2. Create a project
    proj_name = "test_run_proj"
    proj_desc = "My custom description"
    proj_file = project_manager.create_project(proj_name, proj_desc)

    assert proj_file.exists()
    with open(proj_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["name"] == proj_name
    assert data["description"] == proj_desc
    assert set(data.keys()) >= {"name", "description", "crawl", "preprocess", "classification"}

    # 3. Available projects
    assert project_manager.get_available_projects() == [proj_name]

    # 4. Activate project
    project_manager.activate_project(proj_name)
    assert project_manager.get_active_project() == (proj_name, proj_desc)
    assert project_manager.has_active_project() is True
    assert project_manager.has_active_projects() is True

    # 5. Activating non-existent project raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        project_manager.activate_project("does_not_exist")

    # 6. Deactivate project
    project_manager.deactivate_project()
    assert project_manager.get_active_project() is None
    assert project_manager.has_active_project() is False
    assert project_manager.has_active_projects() is False
