from typing_extensions import Self

from nps_crawling.classification.classification_pipeline import ClassificationPipeline

class ClassificationModel():

    instance = None

    def __new__(cls) -> Self:
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        self._classification: ClassificationPipeline | None = None

    @property
    def classification(self) -> ClassificationPipeline:
        if self._classification is None:
            self._classification = ClassificationPipeline()
        
        return self._classification

    def start_classification(self) -> bool:
        self.classification.classification_workflow()

        return True
