"""
Rival-club content guard for Taraji AI.

HARD editorial rule: Club Africain (EST's arch-rival) must never appear in
anything published to the fan-facing channels - not even coverage of EST
beating them. This guard is deterministic and runs at two points:

- collection time (main.py): rival-mentioning articles are never ingested,
  so no extraction/AI budget is spent on them;
- distribution time (every distributor): last line of defense for articles
  that entered the database by any other path.
"""
import re
from typing import Dict, List, Optional

from utils import log


# Latin-script forms: the club's name plus "clubiste(s)", how francophone
# Tunisian media refer to CA players and fans.
_LATIN_RIVAL = re.compile(r'club\s+africain|clubiste', re.IGNORECASE)

# Arabic: the definite "الأفريقي" in any hamza/final-ya spelling, with or
# without attached conjunction/preposition clitics (والأفريقي، بالأفريقي،
# للأفريقي...). The indefinite adjective ("لقب أفريقي", "لاعب أفريقي") and
# feminine forms ("البطولة الأفريقية") do not match.
_ARABIC_RIVAL = re.compile(r'\b[وف]?(?:[بك]ال|لل|ال)[أاإ]فريق[يى]\b')

# "الأفريقي" is also an ordinary adjective in continental-football vocabulary
# ("السوبر الأفريقي", "الاتحاد الأفريقي"). A match whose preceding word ends
# with one of these stems is CAF/continental phrasing, not the club; endswith
# also covers clitic forms of the preceder (بالسوبر، والاتحاد). Anything not
# provably benign is treated as the club - over-blocking an EST story is
# recoverable, publishing a rival story is not.
_BENIGN_PRECEDING_STEMS = (
    'تحاد',    # الاتحاد الأفريقي - CAF
    'سوبر',    # السوبر الأفريقي - CAF Super Cup
    'بطل',     # البطل الأفريقي
    'بطال',    # دوري الأبطال الأفريقي
    'منتخب',   # المنتخب الأفريقي
    'مستوى',   # المستوى الأفريقي
    'صعيد',    # الصعيد الأفريقي
    'لقب',     # اللقب الأفريقي
    'تتويج',   # التتويج الأفريقي
    'مشوار',   # المشوار الأفريقي - continental campaign
    'حلم',     # الحلم الأفريقي
)

_PUNCTUATION = '«»"\'“”()[]{}.,:;!?؟،؛-'


def mentions_rival(text: str) -> Optional[str]:
    """Return the rival mention found in the text, or None if it is clean."""
    if not text:
        return None

    match = _LATIN_RIVAL.search(text)
    if match:
        return match.group(0)

    for match in _ARABIC_RIVAL.finditer(text):
        preceding = text[:match.start()].split()
        prev = preceding[-1].strip(_PUNCTUATION) if preceding else ''
        if not prev.endswith(_BENIGN_PRECEDING_STEMS):
            return match.group(0)

    return None


def rival_mention_in_article(article: Dict) -> Optional[str]:
    """Check every article field that reaches (or feeds) a published post.

    The body is included even though posts only carry title + summaries:
    summaries are AI-generated from the body, so a rival mention there can
    surface in the output.
    """
    text = ' '.join(filter(None, [
        article.get('title'),
        article.get('summary'),
        article.get('summary_ar'),
        article.get('content'),
        article.get('description'),
    ]))
    return mentions_rival(text)


def screen_articles(db, articles: List[Dict], channel: str) -> List[Dict]:
    """Drop rival-mentioning articles from a distribution batch.

    Vetoed articles get a 'vetoed' distribution_log row so they permanently
    leave the unpublished queue for that channel instead of being refetched
    and re-skipped on every run.
    """
    cleared = []
    for article in articles:
        matched = rival_mention_in_article(article)
        if matched:
            log.warning(f"🚫 Rival-club veto ({matched!r}): {article['title'][:70]}")
            db.mark_published(article['id'], channel, None, 'vetoed')
        else:
            cleared.append(article)
    return cleared
