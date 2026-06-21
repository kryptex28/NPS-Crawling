"""
Remove existing NPS-related category JSONs and regenerate them (same logic as Category-Generation.ipynb).

Run from repo root:
    python train/regenerate_category_configs.py
"""
from __future__ import annotations

import json
from pathlib import Path


def find_repo_root() -> Path:
    p = Path(__file__).resolve().parents[1]
    if (p / "pyproject.toml").exists():
        return p
    raise FileNotFoundError("Run from NPS-Crawling repository root.")


def main() -> None:
    root = find_repo_root()
    cat_root = (
        root
        / "src"
        / "nps_crawling"
        / "classification"
        / "configurations"
        / "categories"
    )
    for sub in ("NPS Category", "NPS Value Category", "Has Numeric NPS", "NPS All", "TestCat"):
        d = cat_root / sub
        if not d.is_dir():
            continue
        for f in d.glob("*.json"):
            f.unlink()
            print("Deleted", f)

    # Import after optional cleanup so package sees fresh paths
    from nps_crawling.classification.categories.category import (
        ClassificationCategory,
        ClassificationProperty,
        ClassificationType,
    )

    nps_category_properties = [
        ClassificationProperty(
            name="KPI_CURRENT_VALUE",
            description="The text reports a specific NPS value.",
            type=ClassificationType.BOOLEAN,
        ),
        ClassificationProperty(
            name="KPI_TREND",
            description="The text describes change over time.",
            type=ClassificationType.BOOLEAN,
        ),
        ClassificationProperty(
            name="KPI_HISTORICAL_COMPARISON",
            description="The text explicitly compares NPS against a previous period.",
            type=ClassificationType.BOOLEAN,
        ),
        ClassificationProperty(
            name="TARGET_OUTLOOK",
            description="The text expresses a future goal, target, ambition, forecast, or expected future NPS.",
            type=ClassificationType.BOOLEAN,
        ),
        ClassificationProperty(
            name="NPS_GOAL_REACHED",
            description="The text states that an NPS target or objective has been met or exceeded.",
            type=ClassificationType.BOOLEAN,
        ),
        ClassificationProperty(
            name="METHODOLOGY_DEFINITION",
            description="The text explains what NPS is, how it is calculated, or what it measures.",
            type=ClassificationType.BOOLEAN,
        ),
        ClassificationProperty(
            name="QUALITATIVE_ONLY",
            description="NPS is mentioned meaningfully but none of the other labels apply.",
            type=ClassificationType.BOOLEAN,
        ),
    ]
    nps_value_category_properties = [
        ClassificationProperty(
            name="nps_value_fix",
            description="Direct NPS value.",
            type=ClassificationType.FLOAT,
        ),
        ClassificationProperty(
            name="nps_competition_industry",
            description="Industry benchmark or competitor NPS value.",
            type=ClassificationType.FLOAT,
        ),
        ClassificationProperty(
            name="nps_value_over",
            description="Threshold value associated with above, over, greater than, more than, or at least.",
            type=ClassificationType.FLOAT,
        ),
        ClassificationProperty(
            name="nps_value_below",
            description="Threshold value associated with below, under, less than, or at most.",
            type=ClassificationType.FLOAT,
        ),
        ClassificationProperty(
            name="nps_goal_value",
            description="Explicit NPS target value, only if value is at least 20.",
            type=ClassificationType.FLOAT,
        ),
        ClassificationProperty(
            name="nps_goal_change",
            description="Planned improvement amount such as improve by 10, increase by 5, or raise by 7.",
            type=ClassificationType.FLOAT,
        ),
    ]
    has_numeric_nps_property = ClassificationProperty(
        name="has_numeric_nps",
        description="True if the text contains at least one explicit numeric NPS value.",
        type=ClassificationType.BOOLEAN,
    )
    all_classification_properties = [
        *nps_category_properties,
        *nps_value_category_properties,
        has_numeric_nps_property,
    ]
    prompt_base = """You are an expert at analyzing text to identify and extract information about Net Promoter Score (NPS). NPS is a widely used metric that measures customer loyalty and satisfaction by asking customers how likely they are to recommend a product or service to others. Your task is to read the provided text and determine whether it contains specific information related to NPS, as defined by the following properties:"""
    prompt_base_nps_category = (
        prompt_base
        + " Focus on the multi-label boolean dimensions only (whether each statement type applies)."
    )
    prompt_base_nps_value = (
        prompt_base
        + " Focus on extracting numeric NPS-related values only (direct value, benchmarks, thresholds, goals)."
    )
    prompt_base_has_numeric = (
        prompt_base
        + " Answer only whether the text states at least one concrete numeric NPS value."
    )

    csv_path = str((root / "train" / "ground_truth_final.csv").resolve())

    categories = {
        "NPS Category": ClassificationCategory(
            "NPS Category",
            nps_category_properties,
            prompt_base_nps_category,
            csv_path=csv_path,
        ),
        "NPS Value Category": ClassificationCategory(
            "NPS Value Category",
            nps_value_category_properties,
            prompt_base_nps_value,
            csv_path=csv_path,
        ),
        "Has Numeric NPS": ClassificationCategory(
            "Has Numeric NPS",
            [has_numeric_nps_property],
            prompt_base_has_numeric,
            csv_path=csv_path,
            num_examples=6,
        ),
        "NPS All": ClassificationCategory(
            "NPS All",
            all_classification_properties,
            prompt_base,
            csv_path=csv_path,
            num_examples=5,
        ),
    }

    for label, cat in categories.items():
        print(label, "->", cat.config_path, "examples", len(cat.examples))

    pipeline_json = (
        root
        / "src"
        / "nps_crawling"
        / "classification"
        / "configurations"
        / "NPS_ALL_WITH_QWEN.json"
    )
    with open(pipeline_json, encoding="utf-8") as f:
        pipeline = json.load(f)
    for item in pipeline.get("classification_configuration", []):
        cat = item.get("category")
        if isinstance(cat, dict) and cat.get("name") == "NPS All":
            item["category"] = categories["NPS All"].to_dict()
            break
    with open(pipeline_json, "w", encoding="utf-8") as f:
        json.dump(pipeline, f, indent=2, ensure_ascii=False)
    print("Updated", pipeline_json)


if __name__ == "__main__":
    main()
