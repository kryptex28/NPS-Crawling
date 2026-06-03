from enum import Enum

from nps_crawling.classification.categories.category import ClassificationCategory
from nps_crawling.classification.categories.nps_value_category import NPSValueCategory
from nps_crawling.classification.categories.nps_category import NPSCategory
from nps_crawling.classification.categories.has_numeric_nps import HasNumericNPS

class ClassificationTask(str, Enum):
    """Classification task type."""
    NPS_VALUE_CATEGORY = "NPS Value Category"
    NPS_CATEGORY = "NPS Category"
    HAS_NUMERIC_NPS = "Has Numeric NPS"

    def __repr__(self):
        return self.value

_CLASSIFICATION_REGISTRY = {
    ClassificationTask.NPS_VALUE_CATEGORY: NPSValueCategory,
    ClassificationTask.NPS_CATEGORY: NPSCategory,
    ClassificationTask.HAS_NUMERIC_NPS: HasNumericNPS,
}

def get_category(model_name: ClassificationTask) -> ClassificationCategory:
    """Get category instance by name."""
    if model_name not in _CLASSIFICATION_REGISTRY:
        raise ValueError(f"Model '{model_name}' is not registered.")
    model_class = _CLASSIFICATION_REGISTRY[model_name]
    return model_class(name=model_name)