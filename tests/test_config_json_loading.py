import json
from types import SimpleNamespace

import pytest

from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    ClassificationProperty,
    ClassificationType,
)
from nps_crawling.classification.common import (
    config_path_ref,
    load_json_file,
    resolve_config_entry,
    resolve_config_path,
)
from nps_crawling.classification.model_pipeline import ClassificationModelPipeline
from nps_crawling.classification.models.model import ClassificationModel
from nps_crawling.config import Config


@pytest.fixture
def default_category_path():
    return resolve_config_path(
        Config.ROOT_DIR
        / "src/nps_crawling/classification/configurations/categories/Default"
        / "1661ea62d36667f0ef1f0c1ea6fd5281231de88e9e3d016b71bb1e55f8831688.json"
    )


def test_classification_category_from_json(default_category_path, monkeypatch):
    monkeypatch.setattr(
        "nps_crawling.classification.categories.category.os.path.exists",
        lambda _path: True,
    )
    category = ClassificationCategory.from_json(default_category_path)
    assert category.name == "Default"
    assert len(category.properties) == 2


def test_classification_model_from_json(default_category_path):
    model_path = (
        Config.CLASSIFICATION_CONFIG_DIR
        / "Qwen3-8B"
        / "272c5b7bea3979d8a1030935593bab89a415398c05df7ea740879746123d0db7.json"
    )
    if not model_path.is_file():
        pytest.skip("Packaged model config not present")

    data = load_json_file(model_path)
    assert data["class_name"] == "HF_LLM"
    assert data["model_name"] == "Qwen/Qwen3-8B"


def test_resolve_config_entry_accepts_path_dict_and_object(default_category_path, monkeypatch):
    monkeypatch.setattr(
        "nps_crawling.classification.categories.category.os.path.exists",
        lambda _path: True,
    )
    inline = load_json_file(default_category_path)
    category = ClassificationCategory(
        name="Object Category",
        properties=[
            ClassificationProperty(
                name="flag",
                description="A boolean flag.",
                type=ClassificationType.BOOLEAN,
            ),
        ],
        prompt_base="Prompt.",
    )

    from_path = resolve_config_entry(
        config_path_ref(default_category_path),
        from_dict=ClassificationCategory.from_dict,
        from_json=ClassificationCategory.from_json,
    )
    from_inline = resolve_config_entry(
        inline,
        from_dict=ClassificationCategory.from_dict,
        from_json=ClassificationCategory.from_json,
    )
    from_object = resolve_config_entry(
        category,
        from_dict=ClassificationCategory.from_dict,
        from_json=ClassificationCategory.from_json,
    )

    assert from_path.name == "Default"
    assert from_inline.name == "Default"
    assert from_object.name == "Object Category"


def test_pipeline_to_dict_uses_path_references(default_category_path, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "nps_crawling.classification.categories.category.os.path.exists",
        lambda _path: True,
    )
    monkeypatch.setattr(
        "nps_crawling.classification.models.model.os.path.exists",
        lambda _path: True,
    )

    category = ClassificationCategory(
        name="Test Category",
        properties=[
            ClassificationProperty(
                name="flag",
                description="A boolean flag.",
                type=ClassificationType.BOOLEAN,
            ),
        ],
        prompt_base="Test prompt.",
    )
    model_path = (
        Config.ROOT_DIR
        / "src/nps_crawling/classification/configurations/Qwen3-8B"
        / "272c5b7bea3979d8a1030935593bab89a415398c05df7ea740879746123d0db7.json"
    )
    if not model_path.is_file():
        pytest.skip("Packaged model config not present")

    pipeline = SimpleNamespace(
        name="test_pipeline",
        category_model={
            category: SimpleNamespace(config_path=model_path),
        },
    )
    saved = ClassificationModelPipeline.to_dict(pipeline)

    assert saved["name"] == "test_pipeline"
    assert isinstance(saved["classification_configuration"][0]["category"], str)
    assert isinstance(saved["classification_configuration"][0]["model"], str)
    assert "class_name" not in saved["classification_configuration"][0]["category"]


def test_pipeline_from_dict_supports_inline_configs(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "nps_crawling.classification.categories.category.os.path.exists",
        lambda _path: True,
    )
    monkeypatch.setattr(
        "nps_crawling.classification.models.model.os.path.exists",
        lambda _path: True,
    )
    monkeypatch.setattr(Config, "CLASSIFICATION_CONFIG_DIR", tmp_path)
    monkeypatch.setattr(Config, "CLASSIFIED_BASE_PATH", tmp_path / "classified")
    monkeypatch.setattr(
        "nps_crawling.classification.model_pipeline.DbAdapter.ensure_table_exists",
        lambda *args, **kwargs: None,
    )

    mock_model = SimpleNamespace(
        model_name="mock-model",
        config_path=tmp_path / "mock_model.json",
        is_trained=lambda _category: True,
        train=lambda _category: None,
    )
    monkeypatch.setattr(
        ClassificationModelPipeline,
        "_resolve_model",
        staticmethod(lambda _value: mock_model),
    )

    inline = {
        "name": "inline_pipeline",
        "classification_configuration": [
            {
                "category": {
                    "class_name": "ClassificationCategory",
                    "name": "Inline",
                    "properties": [
                        {
                            "name": "flag",
                            "description": "A boolean flag.",
                            "type": "boolean",
                        }
                    ],
                    "prompt_base": "Inline prompt.",
                    "csv_path": None,
                    "examples": [],
                },
                "model": {
                    "class_name": "HF_LLM",
                    "model_name": "Qwen/Qwen3-8B",
                    "model_input": "",
                    "kwargs": {},
                },
            }
        ],
    }

    pipeline = ClassificationModelPipeline.from_dict(inline)
    assert pipeline.name == "inline_pipeline"
    assert len(pipeline.category_model) == 1
