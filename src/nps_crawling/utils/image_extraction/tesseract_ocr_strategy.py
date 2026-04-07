import pytesseract

from nps_crawling.utils.image_extraction.image_extractor_strategy import ImageExtractorStrategy

class TesseractOCRStrategy(ImageExtractorStrategy):

    def __init__(self,
                 lang="eng",
                 config="--psm 3") -> None:
        super().__init__()

        self.lang: str = lang
        self.config: str = config
    
    def extract(self, image_source: str | bytes) -> dict:
        img = self._load_image(image_source)
        text: str = pytesseract.image_to_string(img, lang=self.lang, config=self.config)

        data: dict = pytesseract.image_to_data(img,
                                         output_type=pytesseract.Output.DICT)
        return {
            "text": text.strip(),
            "metadata": {
                "strategy": "tesseract",
                "word_confidences": [
                    c for c in data["conf"] if c != -1
                ],
                "avg_confidence": sum(
                    c for c in data["conf"] if c != -1
                ) / max(len([c for c in data["conf"] if c != -1]), 1),
            },
        }