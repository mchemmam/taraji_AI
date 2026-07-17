"""
Keyword filtering for Taraji AI
Filters articles based on club mentions with smart contextual matching
"""
from typing import List, Tuple, Optional
from rapidfuzz import fuzz

from utils import load_json_config, log
from config import settings
from config.players import all_players, match_variants


class KeywordFilter:
    """Smart keyword filter with contextual matching and negative keywords"""

    def __init__(self, keywords_path: str = None):
        if keywords_path is None:
            keywords_path = settings.CONFIG_DIR / "keywords.json"

        self.keywords = load_json_config(keywords_path)
        self.exact_keywords = self.keywords.get('exact', {})
        self.ambiguous_keywords = self.keywords.get('exact_ambiguous', {})
        self.contextual_keywords = self.keywords.get('contextual', {})
        self.negative_keywords = self.keywords.get('negative', [])

        # Monitored player names (squad departure watch + transfer targets):
        # (lowercased variant, canonical name) pairs for substring matching
        self.player_keywords = [
            (variant.lower(), player['name'])
            for player in all_players()
            for variant in match_variants(player)
        ]

        log.info(f"Keyword filter loaded with {len(self._all_keywords())} keywords "
                 f"and {len(self.player_keywords)} player name variants")

    def _all_keywords(self) -> List[str]:
        """Get all exact keywords (for counting)"""
        all_kw = []
        for lang_kw in self.exact_keywords.values():
            all_kw.extend(lang_kw)
        for lang_kw in self.ambiguous_keywords.values():
            all_kw.extend(lang_kw)
        return all_kw

    @staticmethod
    def _match_exact(keywords_by_lang: dict, text_lower: str,
                     language: str) -> Optional[str]:
        """Return the first keyword found in the text.

        Checks only the given language's keywords when known, all languages
        otherwise.
        """
        if language == 'unknown':
            languages = list(keywords_by_lang.keys())
        else:
            languages = [language] if language in keywords_by_lang else []

        for lang in languages:
            for keyword in keywords_by_lang[lang]:
                if keyword.lower() in text_lower:
                    return keyword
        return None

    def matches(self, text: str, language: str = 'unknown') -> Tuple[bool, Optional[str]]:
        """
        Check if text matches our keywords

        Args:
            text: Text to check
            language: Language code (fr, ar, en, etc.)

        Returns:
            Tuple of (matches: bool, matched_keyword: str or None)
        """
        if not text:
            return False, None

        text_lower = text.lower()

        # Step 1: Unambiguous club names win outright - negative keywords must
        # not veto them, or derby coverage ("Espérance de Tunis bat le Club
        # Africain") gets dropped. False positives that slip through here are
        # caught by the AI relevance check downstream.
        matched = self._match_exact(self.exact_keywords, text_lower, language)
        if matched:
            log.info(f"✅ Matched exact keyword: {matched}")
            return True, matched

        # Step 2: Negative keywords veto all weaker match types below
        for neg_keyword in self.negative_keywords:
            if neg_keyword.lower() in text_lower:
                log.info(f"❌ Filtered out by negative keyword: {neg_keyword}")
                return False, None

        # Step 3: Monitored player names (full-name spellings from
        # players.json). Placed after the negative veto; namesakes that slip
        # through are caught by the AI relevance check downstream.
        for variant, canonical in self.player_keywords:
            if variant in text_lower:
                log.info(f"✅ Matched player name: {canonical} ({variant})")
                return True, f"{canonical} (player)"

        # Step 4: Ambiguous short names (bare "الترجي" is also a substring of
        # "الترجي الجرجيسي"/Zarzis) - only valid once negatives had their say
        matched = self._match_exact(self.ambiguous_keywords, text_lower, language)
        if matched:
            log.info(f"✅ Matched exact keyword: {matched}")
            return True, matched

        # Step 5: Check contextual keywords (require context words nearby)
        for keyword, context_words in self.contextual_keywords.items():
            if keyword.lower() in text_lower:
                # Check if any context word appears in the text
                for context in context_words:
                    if context.lower() in text_lower:
                        log.info(f"✅ Matched contextual keyword: {keyword} + {context}")
                        return True, f"{keyword} (contextual)"

        # Step 6: Fuzzy matching for typos (only for main club name variations)
        main_keywords = [
            'Espérance Sportive de Tunis',
            'Esperance Sportive de Tunis',
            'الترجي الرياضي التونسي',
        ]

        for keyword in main_keywords:
            ratio = fuzz.partial_ratio(keyword.lower(), text_lower)
            if ratio > 85:
                log.info(f"✅ Matched fuzzy keyword: {keyword} (similarity: {ratio}%)")
                return True, f"{keyword} (fuzzy)"

        # No match found
        log.debug(f"❌ No keyword match in text: {text_lower[:100]}...")
        return False, None

    def filter_articles(self, articles: List[dict]) -> List[dict]:
        """
        Filter a list of articles, keeping only relevant ones

        Args:
            articles: List of article dictionaries (must have 'title' and 'content' or 'description')

        Returns:
            Filtered list of articles with 'matched_keyword' field added
        """
        filtered = []

        for i, article in enumerate(articles, 1):
            # Combine title and content/description for matching
            title = article.get('title', '') or ''
            content = article.get('content') or article.get('description') or ''
            text = f"{title} {content}".strip()

            # Get language if available
            language = article.get('language') or 'unknown'

            # Check if matches
            try:
                matches, matched_keyword = self.matches(text, language)
            except Exception as e:
                log.error(f"    ❌ Error in matches(): {e}", exc_info=True)
                matches = False
                matched_keyword = None

            if matches:
                log.info(f"  ✅ Article {i} MATCHED: {matched_keyword}")
                article['matched_keyword'] = matched_keyword
                filtered.append(article)
            else:
                log.debug(f"  ❌ Article {i} filtered out")

        log.info(f"Filtered {len(articles)} articles → {len(filtered)} relevant")
        return filtered


# Convenience function
def create_keyword_filter() -> KeywordFilter:
    """Create keyword filter instance"""
    return KeywordFilter()
