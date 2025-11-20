"""
Google News collector for Taraji AI
"""
from typing import List, Dict
import time
import re

from gnews import GNews

from .base_collector import BaseCollector
from utils import log, clean_text, parse_date
from config import settings


def has_arabic(text: str) -> bool:
    """Check if text contains Arabic characters"""
    arabic_pattern = re.compile(r'[\u0600-\u06FF]')
    return bool(arabic_pattern.search(text))


class GoogleNewsCollector(BaseCollector):
    """Collect news articles from Google News"""

    def __init__(self):
        super().__init__("Google News")

        # Search queries for the club
        self.queries = [
            "Espérance Sportive de Tunis",
            "Esperance Sportive de Tunis",
            "Espérance Tunis",
            "Esperance Tunis",
            "EST Tunis",
            "Taraji football",
            "الترجي الرياضي التونسي",
            "الترجي التونسي",
        ]

        log.info(f"GoogleNewsCollector initialized with {len(self.queries)} queries")

    def collect(self) -> List[Dict]:
        """Collect articles from Google News"""
        all_articles = []
        seen_urls = set()

        for query in self.queries:
            # Detect if query is in Arabic and use appropriate language setting
            is_arabic = has_arabic(query)
            language = 'ar' if is_arabic else settings.GNEWS_LANGUAGE

            log.info(f"Searching Google News for: {query} (language={language})")

            try:
                # Create GNews instance with appropriate language for this query
                gnews = GNews(
                    language=language,
                    country=settings.GNEWS_COUNTRY,
                    period=settings.GNEWS_PERIOD,
                    max_results=settings.GNEWS_MAX_RESULTS
                )

                # Get news for this query
                results = gnews.get_news(query)

                if not results:
                    log.warning(f"⚠️  No results for query: {query}")
                    continue

                log.info(f"✅ Found {len(results)} articles for: {query}")

                # Process results
                for article in results:
                    url = article.get('url')

                    # Skip duplicates
                    if url in seen_urls:
                        continue

                    seen_urls.add(url)

                    # Normalize article structure
                    normalized = self._normalize_article(article, query)
                    all_articles.append(normalized)

                # Be nice to the server - add delay between queries
                time.sleep(2)

            except Exception as e:
                log.error(f"❌ Error collecting for query '{query}': {e}", exc_info=True)
                self.stats['errors'] += 1
                continue

        # Remove exact duplicates by URL
        unique_articles = self._deduplicate_by_url(all_articles)

        log.info(f"Collected {len(unique_articles)} unique articles from Google News")
        return unique_articles

    def _normalize_article(self, article: Dict, query: str) -> Dict:
        """
        Normalize Google News article structure

        Args:
            article: Raw article from gnews
            query: Search query that found this article

        Returns:
            Normalized article dictionary
        """
        return {
            'url': article.get('url', ''),
            'title': clean_text(article.get('title', '')),
            'description': clean_text(article.get('description', '')),
            'published_date': parse_date(article.get('published date', '')),
            'source': article.get('publisher', {}).get('title', 'Unknown'),
            'source_type': 'google_news',
            'search_query': query,
            'collected_date': None,  # Will be set when storing
            'content': None,  # Will be extracted later if needed
            'language': None,  # Will be detected later
            'category': None,  # Will be classified later
            'summary': None,  # Will be generated later
        }

    def _deduplicate_by_url(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles by URL"""
        seen = set()
        unique = []

        for article in articles:
            url = article.get('url')
            if url not in seen:
                seen.add(url)
                unique.append(article)

        removed = len(articles) - len(unique)
        if removed > 0:
            log.debug(f"Removed {removed} duplicate URLs")

        return unique


# Convenience function
def collect_google_news() -> List[Dict]:
    """Collect news from Google News"""
    collector = GoogleNewsCollector()
    return collector.run()
