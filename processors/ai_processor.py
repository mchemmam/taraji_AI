"""
Batched AI processing for Taraji AI using the Gemini API (google-genai SDK).

One API call per collection run handles all new articles at once: relevance
verification, category classification, and a 2-3 sentence summary in the
article's language. This keeps usage far below the Gemini free-tier daily
request quota even at a 15-minute collection cadence.

Falls back to the rule-based classifier + extractive summary per article
when the API is unavailable or the response can't be parsed.
"""
import json
import os
import time
from datetime import date
from typing import List, Dict, Optional, Tuple

from utils import log
from config import settings
from config.players import load_players
from .classifier import create_classifier

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


# Max characters of article content sent to the model per article
MAX_CONTENT_CHARS = 1500
MAX_RETRIES = 2
# Max recently-published titles included for already-covered detection
MAX_RECENT_TITLES = 40

PROMPT_HEADER_TEMPLATE = """You are processing news items for a fan news service about the Tunisian football club Espérance Sportive de Tunis (EST, also known as Taraji / الترجي الرياضي التونسي).

Today's date is {today}.
{players_block}{recent_block}
For EACH numbered item below, return a JSON object with:
- "id": the item number (integer, as given)
- "relevant": true only if the item is genuinely about Espérance Sportive de Tunis (the Tunis football club) or specifically about one of the monitored players listed above. Items about other Tunisian clubs that also contain "الترجي"/Espérance/Taraji in their name - e.g. Espérance de Zarzis (الترجي الجرجيسي), ES Sahel - the actress Taraji P. Henson, or other unrelated topics are NOT relevant. For monitored players, beware of namesakes: the item must be about the person described in the list (check club, nationality, position), not someone else with the same name.
- "stale": true if the item rehashes an already-concluded event rather than reporting new information — e.g. a fixture/broadcast/replay listing page for a match played long ago, or an aggregator republishing an old story under a refreshed date. Judge this from the actual event described in the content (compare it against today's date), not from the item's claimed publish date - sources sometimes fake freshness. false if it's genuinely new information.
- "duplicate_of": the id (integer) of an EARLIER item in this batch that covers the same story, or null. Two items cover the same story when a reader learns nothing new from the second one - the same event reported by another source or in another language. A follow-up that adds new information is NOT a duplicate.
- "already_covered": true if the item covers the same story as one in the "Recently covered stories" list above (same rule: nothing new for a reader who saw that story). false otherwise, or if no list was given.
- "category": one of "match", "transfer", "injury", "statement", "finance", "other"
- "summary_fr": a factual 2-3 sentence summary in French, focused on facts concerning Espérance Sportive de Tunis (or, for an item about a monitored player, on that player).
- "summary_ar": the same summary in Arabic.

Return ONLY a JSON array of these objects, one per item, no other text.

Items:
"""

RECENT_BLOCK_TEMPLATE = """
Recently covered stories (already published - for the "already_covered" field):
{titles}
"""

PLAYERS_BLOCK_HEADER = """
Monitored players - an item specifically about one of these individuals IS relevant even when the club is not mentioned:
"""


class AIProcessor:
    """Batched relevance check + classification + summarization via Gemini"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model = settings.GEMINI_MODEL
        self.client = None
        self.requests_made = 0
        self._fallback_classifier = create_classifier()
        self._players_block = self._build_players_block()

        if not GENAI_AVAILABLE:
            log.warning("google-genai not installed - using rule-based fallback only")
        elif not self.api_key:
            log.warning("No GEMINI_API_KEY found - using rule-based fallback only")
        else:
            try:
                self.client = genai.Client(api_key=self.api_key)
                log.info(f"Gemini client initialized (model: {self.model})")
            except Exception as e:
                log.error(f"Failed to initialize Gemini client: {e}")

    def process_articles(self, articles: List[Dict],
                         recent_titles: Optional[List[str]] = None
                         ) -> Tuple[List[Dict], List[Tuple[Dict, str]]]:
        """
        Enrich articles in place with 'relevant', 'category', 'summary' (FR)
        and 'summary_ar'.

        Sends all articles in a single Gemini call, along with recently
        published titles so the model can flag re-reports of stories we
        already covered (cross-language and cross-source dedup).

        On any failure, falls back to the rule-based classifier and
        extractive summaries, and marks every article relevant (the keyword
        filter already ran upstream).

        Returns (kept_articles, rejected) where rejected is a list of
        (article, reason) pairs - reason is one of 'irrelevant', 'stale',
        'duplicate', 'already_covered'.
        """
        if not articles:
            return [], []

        results = self._gemini_batch(articles, recent_titles) if self.client else None

        if results is None:
            log.warning("Using rule-based fallback for classification/summaries")
            for article in articles:
                article['relevant'] = True
                article['category'] = self._fallback_classify(article)
                article['summary'] = self._extractive_summary(article)
            return articles, []

        by_id = {}
        for r in results:
            if isinstance(r, dict):
                try:
                    by_id[int(r.get('id'))] = r
                except (TypeError, ValueError):
                    continue

        kept = []
        rejected = []
        for i, article in enumerate(articles, 1):
            r = by_id.get(i)
            if r is None:
                # Model skipped this item - keep it with fallback processing
                article['relevant'] = True
                article['category'] = self._fallback_classify(article)
                article['summary'] = self._extractive_summary(article)
                kept.append(article)
                continue

            if not r.get('relevant', True):
                log.info(f"🚫 AI marked irrelevant: {article.get('title', '')[:70]}")
                rejected.append((article, 'irrelevant'))
                continue

            if r.get('stale', False):
                log.info(f"🕰️  AI marked stale/rehashed: {article.get('title', '')[:70]}")
                rejected.append((article, 'stale'))
                continue

            try:
                dup_of = int(r.get('duplicate_of'))
            except (TypeError, ValueError):
                dup_of = None
            if dup_of is not None and dup_of < i:
                log.info(f"👥 AI marked duplicate of item {dup_of}: {article.get('title', '')[:70]}")
                rejected.append((article, 'duplicate'))
                continue

            if r.get('already_covered', False):
                log.info(f"♻️  AI marked already covered: {article.get('title', '')[:70]}")
                rejected.append((article, 'already_covered'))
                continue

            category = r.get('category', 'other')
            if category not in settings.CATEGORIES:
                category = 'other'

            article['relevant'] = True
            article['category'] = category
            article['summary'] = (r.get('summary_fr') or r.get('summary')
                                  or self._extractive_summary(article))
            article['summary_ar'] = r.get('summary_ar')
            kept.append(article)

        log.info(f"AI processing: {len(articles)} articles → {len(kept)} relevant")
        return kept, rejected

    def _gemini_batch(self, articles: List[Dict],
                      recent_titles: Optional[List[str]] = None) -> Optional[List[Dict]]:
        """Make one Gemini call for all articles. Returns parsed list or None."""
        prompt = self._build_prompt(articles, recent_titles)

        for attempt in range(1, MAX_RETRIES + 2):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.2,
                    ),
                )
                self.requests_made += 1
                parsed = json.loads(response.text)
                if isinstance(parsed, list):
                    return parsed
                log.warning(f"Gemini returned non-list JSON: {type(parsed)}")
                return None

            except json.JSONDecodeError as e:
                log.warning(f"Gemini response was not valid JSON: {e}")
                return None
            except Exception as e:
                log.warning(f"Gemini call failed (attempt {attempt}): {e}")
                if attempt <= MAX_RETRIES:
                    time.sleep(5 * attempt)

        return None

    @staticmethod
    def _build_players_block() -> str:
        """Prompt section listing monitored players from players.json."""
        players = load_players()
        if not (players['squad'] or players['targets']):
            return ""

        lines = [PLAYERS_BLOCK_HEADER]
        if players['squad']:
            lines.append("Current EST squad players (departure/loan rumors and performance news are relevant):")
            lines += [f"- {p['name']} ({p['note']})" for p in players['squad']]
        if players['targets']:
            lines.append("Reported EST transfer targets (any transfer/mercato news about them is relevant):")
            lines += [f"- {p['name']} ({p['note']})" for p in players['targets']]
        return "\n".join(lines) + "\n"

    def _build_prompt(self, articles: List[Dict],
                      recent_titles: Optional[List[str]] = None) -> str:
        items = []
        for i, article in enumerate(articles, 1):
            title = article.get('title', '')
            content = (article.get('content') or article.get('description') or '')[:MAX_CONTENT_CHARS]
            source = article.get('source', '')
            items.append(f"--- Item {i} ---\nSource: {source}\nTitle: {title}\nContent: {content}")

        recent_block = ""
        if recent_titles:
            titles = "\n".join(f"- {t}" for t in recent_titles[:MAX_RECENT_TITLES])
            recent_block = RECENT_BLOCK_TEMPLATE.format(titles=titles)

        header = PROMPT_HEADER_TEMPLATE.format(
            today=date.today().isoformat(),
            players_block=self._players_block,
            recent_block=recent_block,
        )
        return header + "\n\n".join(items)

    def _fallback_classify(self, article: Dict) -> str:
        title = article.get('title', '')
        content = article.get('content') or article.get('description') or ''
        return self._fallback_classifier.classify(title, content)

    def _extractive_summary(self, article: Dict, max_sentences: int = 3) -> str:
        """Fallback: first sentences of the content/description."""
        content = (article.get('content') or article.get('description') or '').strip()
        if not content:
            return ""

        sentences = []
        current = []
        for char in content:
            current.append(char)
            if char in '.!?' and len(current) > 20:
                sentences.append(''.join(current).strip())
                current = []
                if len(sentences) >= max_sentences:
                    break

        summary = ' '.join(sentences[:max_sentences]) if sentences else content[:300]
        if len(summary) > 500:
            summary = summary[:497] + '...'
        return summary

    def get_stats(self) -> dict:
        return {
            'requests_made': self.requests_made,
            'gemini_available': self.client is not None,
        }


# Singleton instance
_processor_instance = None


def create_ai_processor() -> AIProcessor:
    """Create or get singleton AI processor instance"""
    global _processor_instance

    if _processor_instance is None:
        _processor_instance = AIProcessor()

    return _processor_instance
