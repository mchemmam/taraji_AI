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
from typing import List, Dict, Optional

from utils import log
from config import settings
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

PROMPT_HEADER_TEMPLATE = """You are processing news items for a fan news service about the Tunisian football club Espérance Sportive de Tunis (EST, also known as Taraji / الترجي الرياضي التونسي).

Today's date is {today}.

For EACH numbered item below, return a JSON object with:
- "id": the item number (integer, as given)
- "relevant": true only if the item is genuinely about Espérance Sportive de Tunis (the Tunis football club). Items about Espérance de Zarzis, ES Sahel, the actress Taraji P. Henson, or other unrelated topics are NOT relevant.
- "stale": true if the item rehashes an already-concluded event rather than reporting new information — e.g. a fixture/broadcast/replay listing page for a match played long ago, or an aggregator republishing an old story under a refreshed date. Judge this from the actual event described in the content (compare it against today's date), not from the item's claimed publish date - sources sometimes fake freshness. false if it's genuinely new information.
- "category": one of "match", "transfer", "injury", "statement", "finance", "other"
- "summary": a factual 2-3 sentence summary. Write it in Arabic if the article is in Arabic, otherwise in French. Focus on facts concerning Espérance Sportive de Tunis.

Return ONLY a JSON array of these objects, one per item, no other text.

Items:
"""


class AIProcessor:
    """Batched relevance check + classification + summarization via Gemini"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model = settings.GEMINI_MODEL
        self.client = None
        self.requests_made = 0
        self._fallback_classifier = create_classifier()

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

    def process_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Enrich articles in place with 'relevant', 'category' and 'summary'.

        Sends all articles in a single Gemini call. On any failure, falls back
        to the rule-based classifier and extractive summaries, and marks every
        article relevant (the keyword filter already ran upstream).

        Returns the same list, with irrelevant articles filtered out.
        """
        if not articles:
            return []

        results = self._gemini_batch(articles) if self.client else None

        if results is None:
            log.warning("Using rule-based fallback for classification/summaries")
            for article in articles:
                article['relevant'] = True
                article['category'] = self._fallback_classify(article)
                article['summary'] = self._extractive_summary(article)
            return articles

        by_id = {r['id']: r for r in results}
        kept = []
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
                continue

            if r.get('stale', False):
                log.info(f"🕰️  AI marked stale/rehashed: {article.get('title', '')[:70]}")
                continue

            category = r.get('category', 'other')
            if category not in settings.CATEGORIES:
                category = 'other'

            article['relevant'] = True
            article['category'] = category
            article['summary'] = r.get('summary') or self._extractive_summary(article)
            kept.append(article)

        log.info(f"AI processing: {len(articles)} articles → {len(kept)} relevant")
        return kept

    def _gemini_batch(self, articles: List[Dict]) -> Optional[List[Dict]]:
        """Make one Gemini call for all articles. Returns parsed list or None."""
        prompt = self._build_prompt(articles)

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

    def _build_prompt(self, articles: List[Dict]) -> str:
        items = []
        for i, article in enumerate(articles, 1):
            title = article.get('title', '')
            content = (article.get('content') or article.get('description') or '')[:MAX_CONTENT_CHARS]
            source = article.get('source', '')
            items.append(f"--- Item {i} ---\nSource: {source}\nTitle: {title}\nContent: {content}")

        header = PROMPT_HEADER_TEMPLATE.format(today=date.today().isoformat())
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
