"""
Article content extractor for Taraji AI using newspaper3k with trafilatura fallback
"""
from newspaper import Article
from utils import log
from typing import Optional, Dict
import trafilatura
import requests


class ContentExtractor:
    """
    Extract full article content from URLs
    """

    def __init__(self, timeout: int = 10):
        """
        Initialize the content extractor

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

    def extract(self, url: str) -> Optional[Dict[str, any]]:
        """
        Extract article content from URL using newspaper3k with trafilatura fallback

        Args:
            url: Article URL

        Returns:
            Dictionary with extracted content or None if failed
        """
        # Resolve Google News redirect URLs to actual URLs
        if 'news.google.com' in url:
            actual_url = self._resolve_google_news_url(url)
            if actual_url and actual_url != url:
                log.debug(f"Resolved Google News redirect: {url[:50]}... -> {actual_url[:50]}...")
                url = actual_url

        # Try newspaper3k first (more structured)
        result = self._extract_with_newspaper(url)

        if result and result.get('text') and len(result['text']) > 100:
            # Check if it's just Google's consent page
            if 'Before you continue to Google' in result['text'][:500]:
                log.debug(f"Got Google consent page, trying trafilatura...")
            else:
                log.debug(f"✅ Extracted with newspaper3k: {url[:50]}...")
                return result

        # Fallback to trafilatura
        log.debug(f"Newspaper3k failed, trying trafilatura: {url[:50]}...")
        result = self._extract_with_trafilatura(url)

        if result and result.get('text') and len(result['text']) > 100:
            # Check if it's just Google's consent page
            if 'Before you continue to Google' not in result['text'][:500]:
                log.debug(f"✅ Extracted with trafilatura: {url[:50]}...")
                return result

        log.warning(f"❌ Failed to extract content from: {url[:80]}...")
        return None

    def _resolve_google_news_url(self, google_url: str) -> Optional[str]:
        """
        Resolve Google News redirect URL to actual article URL

        Args:
            google_url: Google News redirect URL

        Returns:
            Actual article URL or None if failed
        """
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(
                google_url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=True
            )

            # Get final URL after redirects
            final_url = response.url

            # Make sure we didn't land on Google's consent page
            if 'consent.google.com' not in final_url and final_url != google_url:
                return final_url

            return google_url

        except Exception as e:
            log.debug(f"Failed to resolve Google News URL: {e}")
            return google_url

    def _extract_with_newspaper(self, url: str) -> Optional[Dict[str, any]]:
        """
        Extract using newspaper3k

        Args:
            url: Article URL

        Returns:
            Extracted content dictionary or None
        """
        try:
            article = Article(url)
            article.download()
            article.parse()

            # Only return if we got meaningful content
            if not article.text or len(article.text) < 100:
                return None

            return {
                'text': article.text.strip(),
                'authors': article.authors if article.authors else [],
                'publish_date': article.publish_date,
                'top_image': article.top_image,
                'extraction_method': 'newspaper3k'
            }

        except Exception as e:
            log.debug(f"Newspaper3k extraction failed for {url}: {e}")
            return None

    def _extract_with_trafilatura(self, url: str) -> Optional[Dict[str, any]]:
        """
        Extract using trafilatura (fallback)

        Args:
            url: Article URL

        Returns:
            Extracted content dictionary or None
        """
        try:
            # Download HTML
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            # Extract with trafilatura
            text = trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=False,
                no_fallback=False
            )

            if not text or len(text) < 100:
                return None

            return {
                'text': text.strip(),
                'authors': [],
                'publish_date': None,
                'top_image': None,
                'extraction_method': 'trafilatura'
            }

        except Exception as e:
            log.debug(f"Trafilatura extraction failed for {url}: {e}")
            return None


# Singleton instance
_extractor_instance = None


def create_content_extractor() -> ContentExtractor:
    """
    Create or get singleton content extractor instance

    Returns:
        ContentExtractor instance
    """
    global _extractor_instance

    if _extractor_instance is None:
        _extractor_instance = ContentExtractor()

    return _extractor_instance


def extract_content(url: str) -> Optional[Dict[str, any]]:
    """
    Convenience function to extract article content

    Args:
        url: Article URL

    Returns:
        Extracted content dictionary or None
    """
    extractor = create_content_extractor()
    return extractor.extract(url)
