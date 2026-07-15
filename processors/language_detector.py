"""
Language detection for Taraji AI
"""
from typing import Optional
from langdetect import detect, LangDetectException

from utils import log


class LanguageDetector:
    """Detect language of text"""

    def __init__(self):
        self.supported_languages = ['fr', 'ar', 'en', 'es', 'de', 'it', 'pt']

    def detect(self, text: str) -> str:
        """
        Detect language of text

        Args:
            text: Text to analyze

        Returns:
            Language code (fr, ar, en, etc.) or 'unknown'
        """
        if not text or len(text.strip()) < 10:
            return 'unknown'

        try:
            lang = detect(text)
            log.debug(f"Detected language: {lang}")
            return lang

        except LangDetectException as e:
            log.warning(f"Language detection failed: {e}")
            return 'unknown'

    def detect_batch(self, texts: list) -> list:
        """
        Detect languages for multiple texts

        Args:
            texts: List of texts

        Returns:
            List of language codes
        """
        return [self.detect(text) for text in texts]

    def is_supported(self, language: str) -> bool:
        """Check if language is in supported list"""
        return language in self.supported_languages


# Convenience function
def detect_language(text: str) -> str:
    """Detect language of text"""
    detector = LanguageDetector()
    return detector.detect(text)
