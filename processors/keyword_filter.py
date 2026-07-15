"""
Keyword filtering for Taraji AI
Filters articles based on club mentions with smart contextual matching
"""
from typing import List, Tuple, Optional
from rapidfuzz import fuzz

from utils import load_json_config, log
from config import settings


class KeywordFilter:
    """Smart keyword filter with contextual matching and negative keywords"""

    def __init__(self, keywords_path: str = None):
        if keywords_path is None:
            keywords_path = settings.CONFIG_DIR / "keywords.json"

        self.keywords = load_json_config(keywords_path)
        self.exact_keywords = self.keywords.get('exact', {})
        self.contextual_keywords = self.keywords.get('contextual', {})
        self.negative_keywords = self.keywords.get('negative', [])

        log.info(f"Keyword filter loaded with {len(self._all_keywords())} keywords")

    def _all_keywords(self) -> List[str]:
        """Get all exact keywords (for counting)"""
        all_kw = []
        for lang_kw in self.exact_keywords.values():
            all_kw.extend(lang_kw)
        return all_kw

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

        # Step 1: Check negative keywords first (highest priority)
        for neg_keyword in self.negative_keywords:
            if neg_keyword.lower() in text_lower:
                log.info(f"❌ Filtered out by negative keyword: {neg_keyword}")
                return False, None

        # Step 2: Check exact matches for the specific language
        if language != 'unknown' and language in self.exact_keywords:
            for keyword in self.exact_keywords[language]:
                if keyword.lower() in text_lower:
                    log.info(f"✅ Matched exact keyword [{language}]: {keyword}")
                    return True, keyword

        # Step 3: Check all languages if language is unknown
        if language == 'unknown':
            for lang, keywords in self.exact_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        log.info(f"✅ Matched exact keyword [{lang}]: {keyword}")
                        return True, keyword

        # Step 4: Check contextual keywords (require context words nearby)
        for keyword, context_words in self.contextual_keywords.items():
            if keyword.lower() in text_lower:
                # Check if any context word appears in the text
                for context in context_words:
                    if context.lower() in text_lower:
                        log.info(f"✅ Matched contextual keyword: {keyword} + {context}")
                        return True, f"{keyword} (contextual)"

        # Step 5: Fuzzy matching for typos (only for main club name variations)
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
