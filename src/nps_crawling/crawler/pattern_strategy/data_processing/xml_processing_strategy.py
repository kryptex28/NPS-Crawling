import logging

from nps_crawling.crawler.pattern_strategy.data_processing.processing_strategy import ProcessingStrategy

logger = logging.getLogger(__name__)

class XmlProcessingStrategy(ProcessingStrategy):
    def __init__(self) -> None:
        super().__init__()

    def extract(self, response) -> str:
        logger.info(f"Extracting content from {response.url} as XML.")
        return response.text