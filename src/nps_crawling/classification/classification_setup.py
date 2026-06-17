from typing import List

from nps_crawling.classification.categories.category import ClassificationCategory
from nps_crawling.classification.models.model import ClassificationModel

class ClassificationPipeline:
    def __init__(self, model : ClassificationModel, categories : List[ClassificationCategory]):
        pass