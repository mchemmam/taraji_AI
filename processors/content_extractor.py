"""
Article content extractor for Taraji AI.

Decodes Google News redirect URLs (news.google.com/rss/articles/...) into the
real article URL, then extracts the main text with trafilatura.
"""
from typing import Optional, Dict

import requests
import trafilatura
from googlenewsdecoder import gnewsdecoder

from utils import log
from config import settings


class ContentExtractor:
    """Extract full article content from URLs"""

    def __init__(self, timeout: int = None):
        self.timeout = timeout or settings.EXTRACTION_TIMEOUT
        self.user_agent = (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
        )

    def extract(self, url: str) -> Optional[Dict]:
        """
        Extract article content from a URL.

        Returns a dict with 'text', 'top_image', 'resolved_url',
        'extraction_method' — or None if extraction failed.
        """
        resolved_url = self.resolve_url(url)

        result = self._extract_with_trafilatura(resolved_url)
        if result:
            result['resolved_url'] = resolved_url
            log.debug(f"✅ Extracted {len(result['text'])} chars from: {resolved_url[:80]}")
            return result

        log.debug(f"❌ Failed to extract content from: {resolved_url[:80]}")
        return None

    def resolve_url(self, url: str) -> str:
        """
        Resolve a Google News redirect URL to the real article URL.

        Google News RSS links are base64-encoded redirects that article
        extractors cannot follow; gnewsdecoder decodes them offline/via API.
        Non-Google URLs are returned unchanged.
        """
        if 'news.google.com' not in url:
            return url

        try:
            decoded = gnewsdecoder(url, interval=1)
            if decoded.get('status') and decoded.get('decoded_url'):
                return decoded['decoded_url']
            log.debug(f"gnewsdecoder could not decode: {decoded.get('message', 'unknown error')}")
        except Exception as e:
            log.debug(f"gnewsdecoder failed for {url[:80]}: {e}")

        return url

    def _extract_with_trafilatura(self, url: str) -> Optional[Dict]:
        """Download the page and extract the main article text and image."""
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            text = trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=False,
            )

            if not text or len(text) < settings.MIN_ARTICLE_LENGTH:
                return None

            metadata = trafilatura.extract_metadata(response.text)
            top_image = metadata.image if metadata and metadata.image else None

            return {
                'text': text.strip(),
                'authors': [metadata.author] if metadata and metadata.author else [],
                'top_image': top_image,
                'extraction_method': 'trafilatura',
            }

        except Exception as e:
            log.debug(f"Trafilatura extraction failed for {url[:80]}: {e}")
            return None


# Singleton instance
_extractor_instance = None


def create_content_extractor() -> ContentExtractor:
    """Create or get singleton content extractor instance"""
    global _extractor_instance

    if _extractor_instance is None:
        _extractor_instance = ContentExtractor()

    return _extractor_instance


def extract_content(url: str) -> Optional[Dict]:
    """Convenience function to extract article content"""
    extractor = create_content_extractor()
    return extractor.extract(url)
