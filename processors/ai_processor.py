"""
Batched AI processing for Taraji AI using the Gemini API (google-genai SDK).

One API call per collection run handles all new articles at once: relevance
verification, category classification, and a 2-3 sentence summary in the
article's language. Free-tier daily quotas are ~20 requests per model
(settings.GEMINI_MODELS), so the call walks a chain of models, skipping to
the next bucket on a quota error.

FAIL CLOSED: when no model answers, articles are NOT processed and NOT
published - the caller defers them to the next run, where they are
re-collected. The old behavior (mark everything relevant and post it
unfiltered) put five wrong-club articles on the live channels on
2026-07-16; never reintroduce it.
"""
import json
import os
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple

from utils import log
from config import settings
from config.players import load_players

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


def _utcnow() -> datetime:
    """Naive UTC now, comparable to the DB's CURRENT_TIMESTAMP values.

    collected_date is stored as naive UTC. datetime.now() only matched it
    because GitHub runners run on UTC; on a CEST laptop the update cooldown
    was silently computed two hours short.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Max characters of article content sent to the model per article
MAX_CONTENT_CHARS = 1500
# Max recently-published stories included for already-covered detection
MAX_RECENT_STORIES = 40
# Max characters of each published summary shown in the recent-stories block
MAX_RECENT_SUMMARY_CHARS = 300

PROMPT_HEADER_TEMPLATE = """You are processing news items for a fan news service about the Tunisian football club Espérance Sportive de Tunis (EST, also known as Taraji / الترجي الرياضي التونسي).

Today's date is {today}.
{players_block}{recent_block}
For EACH numbered item below, return a JSON object with:
- "id": the item number (integer, as given)
- "relevant": true only if the item is genuinely about Espérance Sportive de Tunis (the Tunis football club) or specifically about one of the monitored players listed above. Items about other Tunisian clubs that also contain "الترجي"/Espérance/Taraji in their name - e.g. Espérance de Zarzis (الترجي الجرجيسي), ES Sahel - the actress Taraji P. Henson, or other unrelated topics are NOT relevant. For monitored players, beware of namesakes: the item must be about the person described in the list (check club, nationality, position), not someone else with the same name. However, an item about ANY player signing for, joining, leaving or playing for Espérance Sportive de Tunis itself IS relevant, whether or not that player appears in the monitored list.
- "stale": true if the item rehashes an already-concluded event rather than reporting new information — e.g. a fixture/broadcast/replay listing page for a match played long ago, or an aggregator republishing an old story under a refreshed date. Judge this from the actual event described in the content (compare it against today's date), not from the item's claimed publish date - sources sometimes fake freshness. false if it's genuinely new information.
- "duplicate_of": the id (integer) of an EARLIER item in this batch that covers the same story, or null. Two items cover the same story when a reader learns nothing new from the second one - the same event reported by another source or in another language. A follow-up that adds new information is NOT a duplicate. When a later item duplicates an earlier one but mentions extra material details, still mark it as a duplicate - and fold those details into the EARLIER item's summaries.
- "already_covered": true if the item covers the same story as one in the "Recently covered stories" list above - the same event, whatever the source or language. false otherwise, or if no list was given.
- "covers": only meaningful when "already_covered" is true, otherwise null. The tag number of the story it covers, as an integer (for "[S7]" return 7). If it continues several, give the most recent one - the lowest number, since the list is newest first.
- "contradicts": only meaningful when "already_covered" is true, otherwise false. True when this item REVERSES, CANCELS, CORRECTS or DENIES something we already told our readers - a signing called off, a deal collapsing, a player staying after a reported departure, a club denying a reported fact, a decision overturned. We announced the opposite; leaving fans with the wrong story is the worst outcome there is, so judge this generously - if the item cannot be true at the same time as our published line, it contradicts. When "contradicts" is true, also fill "update_details".
- "update_details": only meaningful when "already_covered" is true, otherwise null. Set it when this item carries a material new development in that story - something a reader who saw our earlier post still does not know: a rumored or negotiated move becoming OFFICIAL, a concrete fee/amount, a medical/signing date, a contract length, a collapse or U-turn. Before setting it, scan EVERY line of the "Recently covered stories" list, not just one - especially any line already framed "Mise à jour :"/"تحديث:": if any of them already conveys this same development, then it is NOT new, leave it null (we already posted it). These are NOT updates, leave null: another outlet reporting the same thing, a reworded rumor with no new fact, a farewell/tribute/reaction/thank-you message, a player interview about an already-known move, or a pure opinion/preview piece. When unsure, use null.
- "category": one of "match", "transfer", "injury", "statement", "finance", "other"
- "summary_fr": a factual 2-3 sentence summary in French, focused on facts concerning Espérance Sportive de Tunis (or, for an item about a monitored player, on that player). When "update_details" is set, start with "Mise à jour :" and focus on the NEW facts, recalling the covered story in half a sentence at most.
- "summary_ar": the same summary in Arabic (when "update_details" is set, start with "تحديث:").

Return ONLY a JSON array of these objects, one per item, no other text.

Items:
"""

RECENT_BLOCK_TEMPLATE = """
Recently covered stories (already published - for the "already_covered", "covers" and "update_details" fields), each tagged [S1], [S2], ... Each "published:" line is exactly what our readers were told:
{titles}
"""

PLAYERS_BLOCK_HEADER = """
Monitored players - an item specifically about one of these individuals IS relevant even when the club is not mentioned:
"""


class AIProcessor:
    """Batched relevance check + classification + summarization via Gemini"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.models = settings.GEMINI_MODELS
        self.client = None
        self.requests_made = 0
        self.last_model_used = None
        self._players_block = self._build_players_block()

        if not GENAI_AVAILABLE:
            log.warning("google-genai not installed - articles will be deferred, not published")
        elif not self.api_key:
            log.warning("No GEMINI_API_KEY found - articles will be deferred, not published")
        else:
            try:
                self.client = genai.Client(api_key=self.api_key)
                log.info(f"Gemini client initialized (model chain: {', '.join(self.models)})")
            except Exception as e:
                log.error(f"Failed to initialize Gemini client: {e}")

    def process_articles(self, articles: List[Dict],
                         recent_stories: Optional[List[Dict]] = None
                         ) -> Tuple[List[Dict], List[Tuple[Dict, str]], bool]:
        """
        Enrich articles in place with 'relevant', 'category', 'summary' (FR)
        and 'summary_ar'.

        Sends all articles in a single Gemini call (walking the model chain
        on quota errors), along with recently published stories (title +
        published summary) so the model can flag re-reports of stories we
        already covered (cross-language and cross-source dedup). A re-report
        that adds material new facts vs. the published summary is kept as an
        update post ('is_update' set, summaries framed as "Mise à jour")
        instead of being rejected.

        Returns (kept_articles, rejected, ai_available). rejected is a list
        of (article, reason) pairs - reason is one of 'irrelevant', 'stale',
        'duplicate', 'already_covered'. ai_available=False means NO article
        was judged (every model failed/exhausted): the caller must defer the
        batch to a later run - never publish unjudged articles.
        """
        if not articles:
            return [], [], True

        results = self._gemini_batch(articles, recent_stories) if self.client else None

        if results is None:
            if not self.client:
                log.error("Gemini client not configured (GEMINI_API_KEY) - "
                          "deferring batch, nothing will be published unjudged")
            return [], [], False

        by_id = {}
        for r in results:
            if isinstance(r, dict):
                try:
                    by_id[int(r.get('id'))] = r
                except (TypeError, ValueError):
                    continue

        # When each running story was last posted about, keyed by story_key.
        # Updated in the loop below so two updates to the same story inside
        # one batch can't both land.
        story_posted_at = self._story_posted_at(recent_stories)

        kept = []
        rejected = []
        deferred = 0
        for i, article in enumerate(articles, 1):
            r = by_id.get(i)
            if r is None:
                # No verdict for this item (model truncated or mis-numbered
                # its output). Publishing it unjudged would re-open the
                # 2026-07-16 fail-open hole (wrong-club posts), so defer it:
                # neither kept nor rejected, the URL stays unknown and is
                # re-collected and re-judged on the next run.
                deferred += 1
                log.warning(f"⏭️  No AI verdict for item {i} - deferred: "
                            f"{article.get('title', '')[:70]}")
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
                update = r.get('update_details')
                update = update.strip() if isinstance(update, str) else ''
                has_update = bool(update) and update.lower() not in ('null', 'none')
                # An update judgment needs the article body: when extraction
                # failed the model saw only the title and cannot tell a
                # material new fact from a reworded headline, so title-only
                # "updates" were pure noise (2026-07: several empty Mosaique/
                # Nessma re-reports posted as "Mise à jour"). Require content.
                if has_update and not (article.get('content') or '').strip():
                    log.info(f"♻️  Update suppressed (title-only, no content): "
                             f"{article.get('title', '')[:70]}")
                    has_update = False
                # One update per story per cooldown window: a hot saga always
                # supplies another "material" angle, so materiality alone
                # never converges (Tougaï produced 8 posts in 3 days).
                # A contradiction is exempt: when the story reverses, our
                # readers are holding a line we have since disproved, and
                # "we already posted about this recently" is the very reason
                # the correction has to go out, not a reason to hold it.
                story_key = self._covered_story_key(r, recent_stories)
                contradicts = bool(r.get('contradicts'))
                if has_update and contradicts:
                    log.info(f"⚠️  Contradiction of a published story - cooldown "
                             f"bypassed: {article.get('title', '')[:70]}")
                if has_update and not contradicts:
                    blocked_for = self._cooldown_remaining(story_key, story_posted_at)
                    if blocked_for is not None:
                        log.info(f"♻️  Update suppressed ({blocked_for:.1f}h left of "
                                 f"{settings.UPDATE_COOLDOWN_HOURS}h story cooldown): "
                                 f"{article.get('title', '')[:70]}")
                        has_update = False
                if has_update:
                    log.info(f"🔄 Update to a covered story ({update[:70]}): "
                             f"{article.get('title', '')[:70]}")
                    article['is_update'] = True
                    # Inherit the story's key so this post starts the next
                    # cooldown window instead of founding a new story.
                    if story_key:
                        article['story_key'] = story_key
                        story_posted_at[story_key] = _utcnow()
                else:
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
            # A brand-new story founds its own group; updates already
            # inherited the key of the story they continue.
            article.setdefault('story_key', uuid.uuid4().hex)
            kept.append(article)

        log.info(f"AI processing: {len(articles)} articles → {len(kept)} relevant"
                 + (f" ({deferred} deferred without verdict)" if deferred else ""))
        return kept, rejected, True

    def _gemini_batch(self, articles: List[Dict],
                      recent_stories: Optional[List[Dict]] = None) -> Optional[List[Dict]]:
        """One batched call, walking the model chain. Returns parsed list or None.

        Each model has its own free-tier daily bucket, so a quota error
        (429/RESOURCE_EXHAUSTED) moves straight to the next model - sleeping
        and retrying the same model cannot refill a daily quota. Transient
        errors (503 overload etc.) get one short retry per model.
        """
        prompt = self._build_prompt(articles, recent_stories)

        for model in self.models:
            for attempt in (1, 2):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type='application/json',
                            temperature=0.2,
                        ),
                    )
                    self.requests_made += 1
                    parsed = json.loads(response.text)
                    if isinstance(parsed, list):
                        if model != self.models[0]:
                            log.info(f"Gemini batch served by fallback model {model}")
                        self.last_model_used = model
                        return parsed
                    log.warning(f"{model} returned non-list JSON: {type(parsed)}")
                    break  # malformed output - try the next model, not the same one

                except json.JSONDecodeError as e:
                    log.warning(f"{model} response was not valid JSON: {e}")
                    break  # next model
                except Exception as e:
                    self.requests_made += 1
                    message = str(e)
                    if 'RESOURCE_EXHAUSTED' in message or '429' in message[:16]:
                        log.info(f"{model} daily quota exhausted - trying next model")
                        break  # next bucket, retrying here is pointless
                    log.warning(f"{model} call failed (attempt {attempt}): {message[:200]}")
                    if attempt == 1:
                        time.sleep(5)

        log.error("All Gemini models failed or exhausted - batch will be deferred")
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

    @staticmethod
    def _story_posted_at(recent_stories: Optional[List[Dict]]) -> Dict[str, datetime]:
        """Newest publication time per story_key among the recent stories."""
        posted: Dict[str, datetime] = {}
        for story in recent_stories or []:
            key = story.get('story_key')
            when = story.get('collected_date')
            if not key or not when:
                continue
            if isinstance(when, str):
                try:
                    when = datetime.fromisoformat(when)
                except ValueError:
                    continue
            if key not in posted or when > posted[key]:
                posted[key] = when
        return posted

    @staticmethod
    def _covered_story_key(result: Dict,
                           recent_stories: Optional[List[Dict]]) -> Optional[str]:
        """story_key of the recent story this result says it covers.

        The model returns the [S<n>] tag number; anything out of range or
        unparseable means we cannot identify the story, and the caller then
        treats the update as un-rate-limitable (see _cooldown_remaining).
        """
        try:
            n = int(result.get('covers'))
        except (TypeError, ValueError):
            return None
        stories = (recent_stories or [])[:MAX_RECENT_STORIES]
        if 1 <= n <= len(stories):
            return stories[n - 1].get('story_key')
        return None

    @staticmethod
    def _cooldown_remaining(story_key: Optional[str],
                            story_posted_at: Dict[str, datetime]) -> Optional[float]:
        """Hours left before this story may be updated again, else None.

        None means "let it through": either the story was identified and its
        window has expired, or it could not be identified at all. Blocking
        unidentified updates would hand the model a way to mute the channel
        by omitting one field.
        """
        if not story_key:
            return None
        last = story_posted_at.get(story_key)
        if last is None:
            return None
        elapsed = _utcnow() - last
        window = timedelta(hours=settings.UPDATE_COOLDOWN_HOURS)
        if elapsed >= window:
            return None
        return (window - elapsed).total_seconds() / 3600

    def _build_prompt(self, articles: List[Dict],
                      recent_stories: Optional[List[Dict]] = None) -> str:
        items = []
        for i, article in enumerate(articles, 1):
            title = article.get('title', '')
            content = (article.get('content') or article.get('description') or '')[:MAX_CONTENT_CHARS]
            source = article.get('source', '')
            items.append(f"--- Item {i} ---\nSource: {source}\nTitle: {title}\nContent: {content}")

        recent_block = ""
        if recent_stories:
            lines = []
            for n, story in enumerate(recent_stories[:MAX_RECENT_STORIES], 1):
                lines.append(f"[S{n}] {story.get('title', '')}")
                summary = (story.get('summary') or '').strip()
                if summary:
                    lines.append(f"  published: {summary[:MAX_RECENT_SUMMARY_CHARS]}")
            recent_block = RECENT_BLOCK_TEMPLATE.format(titles="\n".join(lines))

        header = PROMPT_HEADER_TEMPLATE.format(
            today=date.today().isoformat(),
            players_block=self._players_block,
            recent_block=recent_block,
        )
        return header + "\n\n".join(items)

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
            'last_model_used': self.last_model_used,
        }


# Singleton instance
_processor_instance = None


def create_ai_processor() -> AIProcessor:
    """Create or get singleton AI processor instance"""
    global _processor_instance

    if _processor_instance is None:
        _processor_instance = AIProcessor()

    return _processor_instance
