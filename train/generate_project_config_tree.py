"""
Generate or refresh the shared project config tree under projects/configs/.

Run from repo root:
    python train/generate_project_config_tree.py
"""
from __future__ import annotations

from nps_crawling.config import Config
from nps_crawling.project_config import CONFIG_TREE_PATHS, ensure_config_tree


def main() -> None:
    paths = ensure_config_tree(Config.ROOT_DIR)
    print("Config tree (existing files are left unchanged):")
    for section, rel_path in CONFIG_TREE_PATHS.items():
        path = paths[section]
        status = "written" if path.exists() else "missing"
        print(f"  [{section}] {rel_path} ({status})")
    print("\nProject files reference these paths, e.g. projects/nps_project.json")


if __name__ == "__main__":
    main()
