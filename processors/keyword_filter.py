"""
Keyword filtering for Taraji AI
Filters articles based on club mentions with smart contextual matching
"""
import re
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

        # Contextual keywords must match as whole words, and all-caps ones
        # ("EST") case-sensitively: substring-lowercase matching made "EST"
        # hit the French verb "est" - i.e. virtually every French sentence -
        # which flooded the AI step with unrelated Tunisian news and burned
        # the daily Gemini quota (observed 2026-07-17/18 after the French
        # Google News edition shipped).
        self._contextual_patterns = {
            keyword: re.compile(
                rf'\b{re.escape(keyword)}\b',
                0 if keyword.isupper() else re.IGNORECASE,
            )
            for keyword in self.contextual_keywords
        }

        # Exact keywords with an all-caps token ("EST Tunis", "ES Tunis")
        # need the same strictness: as lowercase substrings they hide inside
        # ordinary French ("l'équipe est tunisienne", "les tunisiens").
        self._exact_matchers = self._compile_matchers(self.exact_keywords)
        self._ambiguous_matchers = self._compile_matchers(self.ambiguous_keywords)

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
    def _surface_forms(keyword: str) -> List[str]:
        """Spellings of a keyword that all mean the same club.

        Arabic attaches prepositions as prefixes. Most keep the article
        intact and are found by substring matching anyway ("بالترجي",
        "والترجي"), but "لـ" + "الترجي" contracts to "للترجي" - the
        article's alef is elided, so the literal keyword is no longer a
        substring and the story is dropped without a trace (2026-07-22:
        "3 وديات للترجي في تربص عين دراهم").
        """
        forms = [keyword]
        if keyword.startswith('ال'):
            forms.append('لل' + keyword[2:])
        return forms

    @classmethod
    def _compile_matchers(cls, keywords_by_lang: dict) -> dict:
        """Per-language (keyword, form, pattern) triples for _match_exact.

        Keywords containing an all-caps token get a whole-word,
        case-sensitive pattern; all others keep substring matching
        (pattern None). `keyword` is the canonical name used for logging,
        `form` the actual spelling being looked for.
        """
        compiled = {}
        for lang, keywords in keywords_by_lang.items():
            triples = []
            for keyword in keywords:
                cased = any(len(tok) >= 2 and tok.isupper()
                            for tok in keyword.split())
                for form in cls._surface_forms(keyword):
                    pattern = (re.compile(rf'\b{re.escape(form)}\b')
                               if cased else None)
                    triples.append((keyword, form, pattern))
            compiled[lang] = triples
        return compiled

    @staticmethod
    def _match_exact(matchers_by_lang: dict, text: str, text_lower: str,
                     language: str) -> Optional[str]:
        """Return the first keyword found in the text.

        Checks only the given language's keywords when known, all languages
        otherwise.
        """
        if language == 'unknown':
            languages = list(matchers_by_lang.keys())
        else:
            languages = [language] if language in matchers_by_lang else []

        for lang in languages:
            for keyword, form, pattern in matchers_by_lang[lang]:
                if pattern is not None:
                    if pattern.search(text):
                        return keyword
                elif form.lower() in text_lower:
                    return keyword
        return None

    @staticmethod
    def _is_shouty(text: str) -> bool:
        """True when the text is mostly capitals (headline in ALL CAPS).

        Tells a deliberate abbreviation apart from shouting: in ordinary
        mixed-case prose an all-caps "EST" can only be the club, because
        the French verb and the compass point are written lowercase.
        """
        letters = [c for c in text if c.isalpha()]
        if len(letters) < 12:
            return False
        return sum(c.isupper() for c in letters) / len(letters) > 0.6

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
        matched = self._match_exact(self._exact_matchers, text, text_lower, language)
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
        matched = self._match_exact(self._ambiguous_matchers, text, text_lower, language)
        if matched:
            log.info(f"✅ Matched exact keyword: {matched}")
            return True, matched

        # Step 5: Check contextual keywords (require context words nearby).
        # Whole-word match on the original-case text - see __init__.
        shouty = self._is_shouty(text)
        for keyword, context_words in self.contextual_keywords.items():
            if not self._contextual_patterns[keyword].search(text):
                continue
            # In an ALL-CAPS headline an all-caps "EST" proves nothing - the
            # verb shouts identically - and the context list is no help
            # either, since "Tunis" is a substring of the "TUNISIENS" that
            # ends half the local headlines. Ignore the keyword outright.
            if keyword.isupper() and shouty:
                continue
            # Check if any context word appears in the text
            for context in context_words:
                if context.lower() in text_lower:
                    log.info(f"✅ Matched contextual keyword: {keyword} + {context}")
                    return True, f"{keyword} (contextual)"
            # An all-caps abbreviation in mixed-case text stands on its own:
            # the context list only covers competition/place words, so club
            # news phrased without them was dropped silently (2026-07-22:
            # "L'EST renonce au recrutement Seydou Lamine Sacko",
            # "EST : Kais Attia démissionne").
            if keyword.isupper():
                log.info(f"✅ Matched all-caps abbreviation: {keyword}")
                return True, f"{keyword} (abbreviation)"

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
                # INFO, not debug: silent drops made a GNET "ES Tunis" story
                # undiagnosable (2026-07-19) - the title is the only trace
                log.info(f"  ❌ Article {i} dropped by keyword filter: {title[:90]}")

        log.info(f"Filtered {len(articles)} articles → {len(filtered)} relevant")
        return filtered


# Convenience function
def create_keyword_filter() -> KeywordFilter:
    """Create keyword filter instance"""
    return KeywordFilter()
