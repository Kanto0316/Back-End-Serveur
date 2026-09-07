from abc import ABC, abstractmethod

import pytesseract
from PIL import Image


class OcrProvider(ABC):
    """Replaceable OCR provider contract."""

    @abstractmethod
    def extract_text(self, image: Image.Image) -> str:
        raise NotImplementedError


class TesseractOcrProvider(OcrProvider):
    def extract_text(self, image: Image.Image) -> str:
        return pytesseract.image_to_string(image, lang="fra+eng")
