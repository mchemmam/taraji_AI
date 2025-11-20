"""
RSS Feed collector for Taraji AI
Collects news from Tunisian and Arabic sports news RSS feeds
"""
from typing import List, Dict
import time

import feedparser

from .base_collector import BaseCollector
from utils import log, clean_text, parse_date
from config import settings


class RSSCollector(BaseCollector):
    """Collect news articles from RSS feeds"""

    def __init__(self):
        super().__init__("RSS Feeds")

        # RSS feeds from Tunisian sports news sites
        self.feeds = settings.RSS_FEEDS

        log.info(f"RSSCollector initialized with {len(self.feeds)} feeds")

    def collect(self) -> List[Dict]:
        """Collect articles from RSS feeds"""
        all_articles = []
        seen_urls = set()

        for feed_info in self.feeds:
            feed_url = feed_info['url']
            feed_name = feed_info['name']
            feed_lang = feed_info.get('language', 'unknown')

            log.info(f"Fetching RSS feed: {feed_name} ({feed_lang})")

            try:
                # Parse RSS feed
                feed = feedparser.parse(feed_url)

                if not feed.entries:
                    log.warning(f"⚠️  No entries in feed: {feed_name}")
                    continue

                log.info(f"✅ Found {len(feed.entries)} entries in: {feed_name}")

                # Process entries
                for entry in feed.entries:
                    url = entry.get('link', '')

                    # Skip duplicates
                    if url in seen_urls:
                        continue

                    seen_urls.add(url)

                    # Normalize article structure
                    normalized = self._normalize_article(entry, feed_info)
                    all_articles.append(normalized)

                # Be nice to the server - add delay between feeds
                time.sleep(1)

            except Exception as e:
                log.error(f"❌ Error collecting from feed '{feed_name}': {e}", exc_info=True)
                self.stats['errors'] += 1
                continue

        # Remove exact duplicates by URL
        unique_articles = self._deduplicate_by_url(all_articles)

        log.info(f"Collected {len(unique_articles)} unique articles from RSS feeds")
        return unique_articles

    def _normalize_article(self, entry: Dict, feed_info: Dict) -> Dict:
        """
        Normalize RSS feed entry structure

        Args:
            entry: RSS entry from feedparser
            feed_info: Feed metadata (name, url, language)

        Returns:
            Normalized article dictionary
        """
        # Extract description/summary
        description = ''
        if hasattr(entry, 'summary'):
            description = entry.summary
        elif hasattr(entry, 'description'):
            description = entry.description

        # Extract published date
        published_date = None
        if hasattr(entry, 'published'):
            published_date = parse_date(entry.published)
        elif hasattr(entry, 'updated'):
            published_date = parse_date(entry.updated)

        return {
            'url': entry.get('link', ''),
            'title': clean_text(entry.get('title', '')),
            'description': clean_text(description),
            'published_date': published_date,
            'source': feed_info['name'],
            'source_type': 'rss',
            'search_query': None,
            'collected_date': None,  # Will be set when storing
            'content': None,  # Will be extracted later if needed
            'language': feed_info.get('language', None),  # Will be detected later if not set
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
def collect_rss() -> List[Dict]:
    """Collect news from RSS feeds"""
    collector = RSSCollector()
    return collector.run()
