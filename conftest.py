from pathlib import Path

from nps_crawling.config import Config

# Apply the packaged test project configuration for the pytest session.
Config.apply_project_file(Config.ROOT_DIR / "projects" / "test_project.json")
