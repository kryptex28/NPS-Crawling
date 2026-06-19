from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    ClassificationProperty,
    ClassificationType,
)


def test_classification_category_stable_id_handles_custom_properties(monkeypatch):
    monkeypatch.setattr(
        "nps_crawling.classification.categories.category.os.path.exists",
        lambda _path: True,
    )

    category = ClassificationCategory(
        name="NPS_Complete",
        properties=[
            ClassificationProperty(
                name="KPI_CURRENT_VALUE",
                description="The text reports a specific NPS value.",
                type=ClassificationType.BOOLEAN,
            ),
        ],
        prompt_base="Test prompt base.",
    )

    assert len(category.stable_id) == 64
    assert category.stable_id == category.stable_id