from abc import ABC, abstractmethod
from PIL import Image

import pytesseract
import io
import httpx
import base64


class ImageExtractorStrategy(ABC):
    @abstractmethod
    def extract(self, image_source: str | bytes) -> dict:
        """Returns {'text': str, 'metadata': dict}"""
        pass


    def _load_image(self, source: str | bytes) -> Image.Image:
        if isinstance(source, bytes):
            return Image.open(io.BytesIO(source)).convert("RGB")
        elif isinstance(source, str) and source.startswith("http"):
            response = httpx.get(source, follow_redirects=True)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content)).convert("RGB")
        else:
            return Image.open(source).convert("RGB")
    