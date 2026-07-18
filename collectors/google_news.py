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
from config.players import all_players

# Player names OR-ed together per Google News query - keeps the number of
# extra requests low (Google rate-limits aggressive clients)
PLAYERS_PER_QUERY = 6


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

        # Monitored players (squad departure watch + transfer targets) get
        # their own queries - rumor articles often never mention the club
        self.player_queries = self._build_player_queries()

        # Per-player searches in foreign Google News editions (players.json
        # "extra_searches") - a player whose transfer market lives outside
        # the en/fr/ar editions (e.g. the Brazilian and Spanish press for
        # Lucas Ribeiro) is invisible to the queries above: Google News has
        # no cross-language search
        self.extra_searches = self._build_extra_searches()

        log.info(f"GoogleNewsCollector initialized with {len(self.queries)} club "
                 f"queries + {len(self.player_queries)} player queries "
                 f"+ {len(self.extra_searches)} foreign-edition player searches")

    @staticmethod
    def _build_player_queries() -> List[str]:
        """OR-batched Google News queries for the monitored players.

        Latin and Arabic names are batched separately so each query stays
        in one script (has_arabic() then routes the query to the Arabic
        edition or to each configured Latin edition).
        """
        players = all_players()
        latin_names = [p['name'] for p in players]
        arabic_names = [p['name_ar'] for p in players if p.get('name_ar')]

        queries = []
        for names in (latin_names, arabic_names):
            for i in range(0, len(names), PLAYERS_PER_QUERY):
                chunk = names[i:i + PLAYERS_PER_QUERY]
                queries.append(" OR ".join(f'"{name}"' for name in chunk))
        return queries

    @staticmethod
    def _build_extra_searches() -> List[tuple]:
        """(query, language, country) searches from players.json extra_searches.

        Each entry names its Google News edition explicitly. The query should
        carry a scoping word when the bare name is ambiguous in that market -
        e.g. '"Lucas Ribeiro" futebol': the bare name in the Brazilian
        edition is dominated by a Joao Pessoa politician (verified
        2026-07-18: 100/100 results were his, 'futebol' cuts it to ~8
        mostly-football ones).
        """
        return [
            (search['query'], search['language'], search['country'])
            for player in all_players()
            for search in player.get('extra_searches', [])
        ]

    def _search_plan(self) -> List[tuple]:
        """Every (query, language, country) request of one collection sweep.

        Arabic-script queries get the Arabic edition; Latin-script queries
        run once per configured Latin edition (en, fr, ...); foreign-edition
        player searches name their own edition.
        """
        plan = []
        for query in self.queries + self.player_queries:
            languages = ['ar'] if has_arabic(query) else settings.GNEWS_LATIN_LANGUAGES
            for language in languages:
                plan.append((query, language, settings.GNEWS_COUNTRY))
        plan.extend(self.extra_searches)
        return plan

    def collect(self) -> List[Dict]:
        """Collect articles from Google News"""
        all_articles = []
        seen_urls = set()

        for query, language, country in self._search_plan():
            log.info(f"Searching Google News for: {query} "
                     f"(language={language}, country={country})")

            try:
                gnews = GNews(
                    language=language,
                    country=country,
                    period=settings.GNEWS_PERIOD,
                    max_results=settings.GNEWS_MAX_RESULTS
                )

                results = gnews.get_news(query)

                if not results:
                    log.warning(f"⚠️  No results for query: {query} (language={language})")
                    continue

                log.info(f"✅ Found {len(results)} articles for: {query} (language={language})")

                for article in results:
                    url = article.get('url')

                    # Skip duplicates
                    if url in seen_urls:
                        continue

                    seen_urls.add(url)

                    normalized = self._normalize_article(article, query)
                    all_articles.append(normalized)

                # Be nice to the server - add delay between queries
                time.sleep(2)

            except Exception as e:
                log.error(f"❌ Error collecting for query '{query}' "
                          f"(language={language}): {e}", exc_info=True)
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
