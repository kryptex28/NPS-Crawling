from nps_crawling.crawler.pattern_strategy.data_processing.processing_strategy import ProcessingStrategy
from nps_crawling.crawler.pattern_strategy.data_processing.pdf_processing_strategy import PdfProcessingStrategy
from nps_crawling.crawler.pattern_strategy.data_processing.txt_processing_strategy import TxtProcessingStrategy
from nps_crawling.crawler.pattern_strategy.data_processing.html_processing_strategy import HtmlProcessingStrategy
from nps_crawling.crawler.pattern_strategy.data_processing.xml_processing_strategy import XmlProcessingStrategy

class ProcessingFactory:
    _strategies: dict[str, type[ProcessingStrategy]] = {
        "html": HtmlProcessingStrategy,
        "htm": HtmlProcessingStrategy,
        "pdf": PdfProcessingStrategy,
        "txt": TxtProcessingStrategy,
        "xml": XmlProcessingStrategy,
    }

    @classmethod
    def create(cls, name: str) -> ProcessingStrategy:
        strategy = cls._strategies.get(name)
        if not strategy:
            raise ValueError(f"Unknown strategy: '{name}'")
        return strategy()