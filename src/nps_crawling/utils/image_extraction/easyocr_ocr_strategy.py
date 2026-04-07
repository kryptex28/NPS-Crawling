import easyocr
import numpy as np

from nps_crawling.utils.image_extraction.image_extractor_strategy import ImageExtractorStrategy

class EasyOCRStrategy(ImageExtractorStrategy):
    def __init__(self, langs=["en"]):
        self.reader = easyocr.Reader(langs)  # downloads model on first run

    def extract(self, image_source: str | bytes) -> dict:
        img = self._load_image(image_source)
        results = self.reader.readtext(np.array(img))
        text = " ".join([res[1] for res in results])
        avg_conf = sum([res[2] for res in results]) / max(len(results), 1)
        return {
            "text": text.strip(),
            "metadata": {"strategy": "easyocr", "avg_confidence": avg_conf * 100}
        }