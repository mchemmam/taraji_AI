"""
Article content extractor for Taraji AI.

Decodes Google News redirect URLs (news.google.com/rss/articles/...) into the
real article URL, then extracts the main text with trafilatura.
"""
from typing import Optional, Dict
from urllib.parse import urlparse, urlunparse

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
        # Why the last extract() call failed ('HTTP 403', 'timeout', ...);
        # None after a success. Callers use it for per-run failure summaries.
        self.last_failure = None

    def extract(self, url: str) -> Optional[Dict]:
        """
        Extract article content from a URL.

        Returns a dict with 'text', 'top_image', 'resolved_url',
        'extraction_method' — or None if extraction failed, with the reason
        left in self.last_failure.
        """
        self.last_failure = None
        resolved_url = self.resolve_url(url)

        result = self._extract_with_trafilatura(resolved_url)
        if result:
            result['resolved_url'] = resolved_url
            log.debug(f"✅ Extracted {len(result['text'])} chars from: {resolved_url[:80]}")
            return result

        # WARNING, not debug: silent extraction failures left the stale
        # guards blind for days - a bot-walled page publishes title-only,
        # with no on-page date and nothing for the AI to judge staleness
        # from (2026-07-19 Nessma/Cloudflare incident)
        log.warning(f"⚠️  Extraction failed ({self.last_failure or 'unknown'}): "
                    f"{resolved_url[:100]}")
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
            log.info(f"gnewsdecoder could not decode: {decoded.get('message', 'unknown error')}")
        except Exception as e:
            log.info(f"gnewsdecoder failed for {url[:80]}: {e}")

        return url

    @staticmethod
    def _fetch_url(url: str) -> str:
        """URL to actually download, which may differ from the canonical one.

        mosaiquefm.net/ar/... and /fr/... return HTTP 200 whose article body
        is JS-rendered - trafilatura gets ~18 chars. The /amp/ mirror of the
        same path is server-rendered and extracts cleanly, so we fetch that.
        The canonical URL is still what gets stored and linked to readers.
        """
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host.endswith('mosaiquefm.net') and not parsed.path.startswith('/amp/'):
            return urlunparse(parsed._replace(path='/amp' + parsed.path))
        return url

    @staticmethod
    def _best_text(html: str) -> Optional[str]:
        """Main article text, retrying with favor_recall if the default is thin.

        Trafilatura's precision-first default misses the body on some
        publishers (Nessma: 254 chars default vs. 958 with favor_recall).
        Only pay for the second parse when the first comes back empty/short,
        then keep whichever pass returned more text.
        """
        text = trafilatura.extract(html, include_comments=False, include_tables=False)
        if text and len(text) >= settings.MIN_ARTICLE_LENGTH:
            return text
        recall = trafilatura.extract(html, include_comments=False,
                                     include_tables=False, favor_recall=True)
        if recall and (not text or len(recall) > len(text)):
            return recall
        return text

    def _extract_with_trafilatura(self, url: str) -> Optional[Dict]:
        """Download the page and extract the main article text and image.

        On failure returns None and records why in self.last_failure.
        """
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(self._fetch_url(url), headers=headers, timeout=self.timeout)
            response.raise_for_status()

            text = self._best_text(response.text)

            if not text:
                self.last_failure = 'no text extracted'
                return None
            if len(text) < settings.MIN_ARTICLE_LENGTH:
                self.last_failure = f'text under {settings.MIN_ARTICLE_LENGTH} chars'
                return None

            metadata = trafilatura.extract_metadata(response.text)
            top_image = metadata.image if metadata and metadata.image else None

            return {
                'text': text.strip(),
                'authors': [metadata.author] if metadata and metadata.author else [],
                'top_image': top_image,
                # Publication date as printed on the page (meta tags/JSON-LD),
                # used to catch stale stories re-served with a fresh feed date
                'page_date': metadata.date if metadata and metadata.date else None,
                'extraction_method': 'trafilatura',
            }

        except requests.exceptions.HTTPError as e:
            self.last_failure = f'HTTP {e.response.status_code}'
            return None
        except requests.exceptions.Timeout:
            self.last_failure = 'timeout'
            return None
        except Exception as e:
            self.last_failure = f'{type(e).__name__}: {str(e)[:80]}'
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
