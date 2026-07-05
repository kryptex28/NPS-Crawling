"""Project configuration defaults, loading, and application to :class:`Config`."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from nps_crawling.classification.common import resolve_config_path


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into a copy of ``base``."""
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


DEFAULT_CRAWL_CONFIG: dict[str, Any] = {
    "query_path": "query",
    "sec_query_limit_count": 10_000,
    "download_delay": 0.2,
}

DEFAULT_PREPROCESS_CONFIG: dict[str, Any] = {
    "version": "version_2",
    "single_keyword_filter": None,
    "single_keyword_filter_strict": True,
    "threshold_keyword_scope": ["nps"],
    "threshold_keyword_scope_strict": True,
    "similarity_threshold_context_window": 0.8,
    "list_of_phrases_to_filter_filings_for": [
        "NPS",
        "net promoter score",
        "nps score",
        "nps of",
        "net promoter",
        "net promotor",
    ],
    "list_of_phrases_to_exclude": [
        "NEW PRODUCT SALES TO TOTAL PRODUCT SALES RATIO (NPS)",
        "NPS Reservation System",
        "NPS Submit software",
        "Nationwide Payment Solutions",
        "NPS Pharmaceuticals",
        "Netezza Performance Server",
        "National Processing Services",
        "Nano-Pulse Stimulation",
        "NPS Reservation System procurement",
        "Net Power Solutions, LLC (“NPS”),",
        "NPSAX",
        "National Prearranged Services",
        "NPS (Network Payment System)",
        "NetBank Payment Systems, Inc. (“NPS”),",
        "The National Park Service’s (“NPS”)",
        "“Novation Proprietary Services” or “NPS”",
        "Neah Power Systems",
        "SNPS",
        "NPS-KBIC PEF",
        "National Product Services",
        "natural products and supplements",
        "National Partnerships",
        "Networked Products & Services",
        "NPS Services",
        "Navitaire Professional Services",
        "National Production Services",
        "National Product Supply System",
        "Nephrology Practice Solutions",
        "network processors",
        "NetApp Private Storage",
        "NPS Purchase Price",
        "NPS 2.X",
        "Netezza",
    ],
    "similarity_reference_text": (
        "net promoter score NPS customer loyalty customer satisfaction "
        "recommend promoters detractors customer experience"
    ),
    "similarity_embedding_model": "all-MiniLM-L6-v2",
    "amount_sentences_included_before": 2,
    "amount_sentences_included_after": 2,
    "max_context_chars_before_keyword": 600,
    "max_context_chars_after_keyword": 600,
    "files_per_chunk": 1000,
}

DEFAULT_CLASSIFICATION_CONFIG: dict[str, Any] = {
    "version": "version_1",
    "random_seed": 42,
    "ground_truth_test_size": 0.5,
    "few_shot_num_examples": 8,
    "few_shot_text_column": "snippet_text_short",
    "few_shot_sample_seed": 43,
    "config_use_name_files": False,
    "embedding_batch_size": 32,
    "llm_batch_size": 8,
    "classification_configuration": [
        {
            "category": (
                "src/nps_crawling/classification/configurations/categories/"
                "NPS Category/c0b1409c1550fcafe2a84875f32bb495385beac0eccf6d09d7e9eac4c266c1f7.json"
            ),
            "model": (
                "src/nps_crawling/classification/configurations/Qwen3-Embedding-4B/"
                "c7d19631b6aeaf2445204a81e778ec2d639ba3c7b02be9416c61e98c5245f3a6.json"
            ),
        },
        {
            "category": (
                "src/nps_crawling/classification/configurations/categories/"
                "Has Numeric NPS/ee63ed22edbeb29b02a976cfdd209f172cff421b5bde2009e1a0c0193f83a38f.json"
            ),
            "model": (
                "src/nps_crawling/classification/configurations/Qwen3-Embedding-4B/"
                "c7d19631b6aeaf2445204a81e778ec2d639ba3c7b02be9416c61e98c5245f3a6.json"
            ),
        },
        {
            "category": (
                "src/nps_crawling/classification/configurations/categories/"
                "NPS Value Category/12b0b9acf27aee693b1d518d68a4b6e9481a53fb55245ab4f08e7c50274f433b.json"
            ),
            "model": (
                "src/nps_crawling/classification/configurations/Qwen3-8B/"
                "6cd28608db45079139f438ef355a2f901be42efb24f9a4ae1155ebbfa8d957ff.json"
            ),
        },
    ],
}

DEFAULT_PROJECT_CONFIG: dict[str, Any] = {
    "crawl": DEFAULT_CRAWL_CONFIG,
    "preprocess": DEFAULT_PREPROCESS_CONFIG,
    "classification": DEFAULT_CLASSIFICATION_CONFIG,
}


CONFIG_TREE_PATHS: dict[str, str] = {
    "crawl": "projects/configs/crawl/default.json",
    "preprocess": "projects/configs/preprocess/version_2.json",
    "classification": "projects/configs/classification/version_1.json",
}


def resolve_project_config_path(ref: str | Path, root_dir: Path) -> Path:
    """Resolve a project config path reference to an existing file."""
    path = Path(ref)
    if path.is_absolute() and path.is_file():
        return path.resolve()

    for candidate in (
        root_dir / path,
        root_dir / "projects" / path,
    ):
        if candidate.is_file():
            return candidate.resolve()

    if path.is_file():
        return path.resolve()

    raise FileNotFoundError(f"Project config JSON not found: {ref}")


def resolve_section_config(
    value: str | dict | None,
    default: dict[str, Any],
    root_dir: Path,
) -> dict[str, Any]:
    """Load a crawl/preprocess/classification section from a path or inline dict."""
    if value is None:
        return copy.deepcopy(default)
    if isinstance(value, str):
        config_path = resolve_project_config_path(value, root_dir)
        with open(config_path, encoding="utf-8") as f:
            loaded = json.load(f)
        if not isinstance(loaded, dict):
            raise ValueError(f"Section config must be a JSON object: {config_path}")
        return deep_merge(default, loaded)
    if isinstance(value, dict):
        return deep_merge(default, value)
    raise TypeError(f"Unsupported section config type: {type(value)!r}")


def ensure_config_tree(root_dir: Path) -> dict[str, Path]:
    """Write shared crawl/preprocess/classification config files if missing."""
    section_defaults = {
        "crawl": DEFAULT_CRAWL_CONFIG,
        "preprocess": DEFAULT_PREPROCESS_CONFIG,
        "classification": DEFAULT_CLASSIFICATION_CONFIG,
    }
    written: dict[str, Path] = {}
    for section, rel_path in CONFIG_TREE_PATHS.items():
        path = root_dir / rel_path
        written[section] = path
        if path.is_file():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(section_defaults[section], f, indent=2, ensure_ascii=False)
    return written


def default_project_data(name: str, description: str = "") -> dict[str, Any]:
    """Return a new project configuration dict that references the shared config tree."""
    return {
        "name": name,
        "description": description,
        "crawl": CONFIG_TREE_PATHS["crawl"],
        "preprocess": CONFIG_TREE_PATHS["preprocess"],
        "classification": CONFIG_TREE_PATHS["classification"],
    }


def load_project_file(project_file: Path, *, root_dir: Path | None = None) -> dict[str, Any]:
    """Load and normalize a project JSON file."""
    project_file = project_file.resolve()
    root_dir = root_dir or project_file.parent.parent

    with open(project_file, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"Project config must be a JSON object: {project_file}")

    name = raw.get("name") or project_file.stem
    description = raw.get("description", "")

    return {
        "name": name,
        "description": description,
        "crawl": resolve_section_config(
            raw.get("crawl"),
            DEFAULT_CRAWL_CONFIG,
            root_dir,
        ),
        "preprocess": resolve_section_config(
            raw.get("preprocess"),
            DEFAULT_PREPROCESS_CONFIG,
            root_dir,
        ),
        "classification": resolve_section_config(
            raw.get("classification"),
            DEFAULT_CLASSIFICATION_CONFIG,
            root_dir,
        ),
    }


def section_config_path(
    section_ref: str | dict | None,
    section: str,
    root_dir: Path,
) -> Path:
    """Resolve the JSON file path for a crawl/preprocess/classification section."""
    if isinstance(section_ref, str):
        return resolve_project_config_path(section_ref, root_dir)
    return root_dir / CONFIG_TREE_PATHS[section]


def active_project_file(root_dir: Path) -> Path | None:
    """Return the active project JSON path, if any."""
    from nps_crawling.utils.project_manager import get_active_project_name

    project_name = get_active_project_name()
    if not project_name:
        return None
    return root_dir / "projects" / f"{project_name}.json"


def save_project_section(
    section: str,
    updates: dict[str, Any],
    root_dir: Path,
) -> Path:
    """Merge ``updates`` into a project section JSON file and return its path."""
    project_file = active_project_file(root_dir)
    if project_file is None or not project_file.is_file():
        raise RuntimeError("No active project loaded.")

    with open(project_file, encoding="utf-8") as f:
        project_raw = json.load(f)

    path = section_config_path(
        project_raw.get(section, CONFIG_TREE_PATHS[section]),
        section,
        root_dir,
    )
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    merged = deep_merge(data, updates)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    return path


def classification_configuration_entries(classification: dict[str, Any]) -> list[dict[str, Any]]:
    """Return category/model pairs from a classification section."""
    entries = classification.get("classification_configuration")
    if entries:
        return entries

    pipeline_ref = classification.get("pipeline")
    if pipeline_ref:
        pipeline_path = resolve_config_path(pipeline_ref)
        with open(pipeline_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("classification_configuration", [])

    return []


def classification_configuration_mapping(
    classification: dict[str, Any],
) -> dict[str | dict, str | dict]:
    """Build a category → model mapping for :class:`ClassificationModelPipeline`."""
    return {
        entry["category"]: entry["model"]
        for entry in classification_configuration_entries(classification)
    }


def classification_path_mapping(classification: dict[str, Any]) -> dict[str, str]:
    """Build resolved category-path → model-path mapping (path references only)."""
    mapping: dict[str, str] = {}
    for entry in classification_configuration_entries(classification):
        category_ref = entry["category"]
        model_ref = entry["model"]
        if isinstance(category_ref, dict) or isinstance(model_ref, dict):
            continue
        category_path = resolve_config_path(category_ref)
        model_path = resolve_config_path(model_ref)
        mapping[str(category_path)] = str(model_path)
    return mapping


def _category_data_from_entry(category_ref: str | dict) -> dict | None:
    if isinstance(category_ref, dict):
        return category_ref
    category_path = resolve_config_path(category_ref)
    with open(category_path, encoding="utf-8") as f:
        return json.load(f)


def project_categories_from_classification(
    classification: dict[str, Any],
) -> list[dict[str, str]]:
    """Load unique property definitions from a classification section."""
    categories: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in classification_configuration_entries(classification):
        cat_data = _category_data_from_entry(entry["category"])
        if not cat_data:
            continue
        for prop in cat_data.get("properties", []):
            prop_name = prop["name"]
            if prop_name in seen:
                continue
            seen.add(prop_name)
            categories.append({"name": prop_name, "type": prop["type"]})
    return categories


def apply_project_data(config_cls, project_data: dict[str, Any], root_dir: Path) -> None:
    """Apply merged project configuration to the :class:`Config` class."""
    crawl = project_data["crawl"]
    preprocess = project_data["preprocess"]
    classification = project_data["classification"]

    config_cls.ACTIVE_PROJECT = project_data["name"]
    config_cls.ACTIVE_PROJECT_DESCRIPTION = project_data.get("description", "")

    config_cls.DATABASE_TABLE_NAME = (
        f"{config_cls.ACTIVE_PROJECT}_db"
        if config_cls.ACTIVE_PROJECT
        else "default"
    )

    config_cls.QUERY_PATH = root_dir / crawl["query_path"]
    config_cls.CRAWL_SEC_QUERY_LIMIT_COUNT = crawl["sec_query_limit_count"]
    config_cls.CRAWL_DOWNLOAD_DELAY = crawl["download_delay"]

    config_cls.PREPROCESSING_VERSION = preprocess["version"]
    config_cls.SINGLE_KEYWORD_FILTER = preprocess["single_keyword_filter"]
    config_cls.SINGLE_KEYWORD_FILTER_STRICT = preprocess["single_keyword_filter_strict"]
    config_cls.THRESHOLD_KEYWORD_SCOPE = preprocess["threshold_keyword_scope"]
    config_cls.THRESHOLD_KEYWORD_SCOPE_STRICT = preprocess["threshold_keyword_scope_strict"]
    config_cls.SIMILARITY_THRESHOLD_CONTEXT_WINDOW = preprocess[
        "similarity_threshold_context_window"
    ]
    config_cls.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR = preprocess[
        "list_of_phrases_to_filter_filings_for"
    ]
    config_cls.LIST_OF_PHRASES_TO_EXCLUDE = preprocess["list_of_phrases_to_exclude"]
    config_cls.SIMILARITY_REFERENCE_TEXT = preprocess["similarity_reference_text"]
    config_cls.SIMILARITY_EMBEDDING_MODEL = preprocess["similarity_embedding_model"]
    config_cls.AMOUNT_SENTENCES_INCLUDED_BEFORE = preprocess[
        "amount_sentences_included_before"
    ]
    config_cls.AMOUNT_SENTENCES_INCLUDED_AFTER = preprocess[
        "amount_sentences_included_after"
    ]
    config_cls.MAX_CONTEXT_CHARS_BEFORE_KEYWORD = preprocess[
        "max_context_chars_before_keyword"
    ]
    config_cls.MAX_CONTEXT_CHARS_AFTER_KEYWORD = preprocess[
        "max_context_chars_after_keyword"
    ]
    config_cls.PREPROCESS_FILES_PER_CHUNK = preprocess["files_per_chunk"]

    config_cls.CLASSIFICATION_VERSION = classification["version"]
    config_cls.CLASSIFICATION_RANDOM_SEED = classification["random_seed"]
    config_cls.CLASSIFICATION_GROUND_TRUTH_TEST_SIZE = classification[
        "ground_truth_test_size"
    ]
    config_cls.CLASSIFICATION_FEW_SHOT_NUM_EXAMPLES = classification[
        "few_shot_num_examples"
    ]
    config_cls.CLASSIFICATION_FEW_SHOT_TEXT_COLUMN = classification[
        "few_shot_text_column"
    ]
    config_cls.CLASSIFICATION_FEW_SHOT_SAMPLE_SEED = classification[
        "few_shot_sample_seed"
    ]
    config_cls.CLASSIFICATION_CONFIG_USE_NAME_FILES = classification[
        "config_use_name_files"
    ]
    config_cls.CLASSIFICATION_EMBEDDING_BATCH_SIZE = classification.get(
        "embedding_batch_size", 32
    )
    config_cls.CLASSIFICATION_LLM_BATCH_SIZE = classification.get(
        "llm_batch_size", 8
    )

    config_cls.CLASSIFICATION_CONFIGURATION = classification_configuration_entries(
        classification,
    )
    config_cls.CLASSIFICATION_CONFIG = classification_path_mapping(classification)
    config_cls.PROJECT_CATEGORIES = project_categories_from_classification(
        classification,
    )

    config_cls._update_project_paths(root_dir)
    config_cls._ensure_project_directories()
