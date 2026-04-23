import logging

from nps_crawling.crawler.pattern_strategy.data_processing.processing_strategy import ProcessingStrategy

logger = logging.getLogger(__name__)

class HtmlProcessingStrategy(ProcessingStrategy):
    def __init__(self) -> None:
        super().__init__()

    def extract(self, response) -> str:
        logger.info(f"Extracting content from {response.url} as HTML.")
        return response.text