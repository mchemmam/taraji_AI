"""
Deterministic re-report detection for Taraji AI.

Aggregators re-publish the same story minutes apart (amp/www variants,
"يلا شووت"-style syndication), and each re-report used to reach the batched
Gemini call just to come back 'already_covered'. With the free tier at ~20
requests/day per model, those wasted calls matter: near-identical titles are
rejected here, before extraction and before any AI budget is spent.

Only near-duplicates of a recent title are caught (conservative threshold);
same-story-different-wording and cross-language re-reports still go to the
AI, whose prompt handles genuine follow-ups correctly.
"""
import re
from typing import Iterable, Optional

from rapidfuzz import fuzz

# Similarity (token_set_ratio, 0-100) at or above which a title counts as a
# re-report. Deliberately high: a false positive silently drops a story,
# a false negative merely costs one batched AI judgment.
RERPORT_THRESHOLD = 90

# Trailing publisher tag as Google News formats it: " - diwanfm.net",
# "| يلا شووت - ysscores.com" etc. Applied repeatedly to peel stacked tags.
_SOURCE_TAG = re.compile(r'\s*[-|–|]\s*[^-|–|]{2,40}$')

_WHITESPACE = re.compile(r'\s+')
_PUNCTUATION = re.compile(r'[«»"\'“”()\[\]{}.,:;!?؟،؛]')


def normalize_title(title: str) -> str:
    """Lowercased title with publisher tags, punctuation and extra spaces removed."""
    normalized = title or ''
    for _ in range(3):
        stripped = _SOURCE_TAG.sub('', normalized)
        if stripped == normalized or not stripped:
            break
        normalized = stripped
    normalized = _PUNCTUATION.sub(' ', normalized.lower())
    return _WHITESPACE.sub(' ', normalized).strip()


def find_rereport(title: str, recent_titles: Iterable[str]) -> Optional[str]:
    """Return the recent title this one re-reports, or None if it is new."""
    normalized = normalize_title(title)
    if not normalized:
        return None
    for recent in recent_titles:
        if fuzz.token_set_ratio(normalized, normalize_title(recent)) >= RERPORT_THRESHOLD:
            return recent
    return None
