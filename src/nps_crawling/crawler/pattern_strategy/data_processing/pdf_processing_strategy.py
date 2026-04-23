import pypdf
import logging
import io

from nps_crawling.crawler.pattern_strategy.data_processing.processing_strategy import ProcessingStrategy

logger = logging.getLogger(__name__)

class PdfProcessingStrategy(ProcessingStrategy):
    def __init__(self) -> None:
        super().__init__()

    def extract(self, response) -> str:
        logger.info(f"Extracting content from {response.url} as PDF.")
        pdf_bytes: bytes = response.body
        reader: pypdf.PdfReader = pypdf.PdfReader(io.BytesIO(pdf_bytes))

        text_parts: list[str] = []

        for page in reader.pages:
            page_text: str = page.extract_text() or ''
            text_parts.append(page_text)

        core_text: str = '\n'.join(text_parts)
        return core_text