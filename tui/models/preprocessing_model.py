from typing_extensions import Self
from nps_crawling.preprocessing.utils import PreProcessingPipeline

class PreprocessingModel():
    instance = None

    def __new__(cls) -> Self:
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        self._preprocessing: PreProcessingPipeline | None = None

    @property
    def preprocessing(self) -> PreProcessingPipeline:
        if self._preprocessing is None:
            self._preprocessing = PreProcessingPipeline()
        return self._preprocessing

    def run_preprocessing(self) -> None:
        self.preprocessing.pre_processing_workflow()