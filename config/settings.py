"""
Configuration settings for Taraji AI
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "taraji_ai.db"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "app.log"
ERROR_LOG_FILE = LOGS_DIR / "errors.log"

# Google News settings
# Google News has no cross-language search: each request targets one edition
# (hl/gl), so every language listed here re-runs all Latin-script queries
# against that edition. 'en' surfaces the international press; 'fr' the
# Tunisian francophone press (Kawarji, RTCI...), which the English edition
# never returns. Arabic-script queries always run against the 'ar' edition.
GNEWS_LATIN_LANGUAGES = ["en", "fr"]
GNEWS_COUNTRY = "TN"   # Tunisia - prioritizes Tunisian news sources
GNEWS_PERIOD = "1d"    # Last 24h - the scheduled runs only need fresh news
GNEWS_MAX_RESULTS = 100  # Max results per query

# Publishers to drop outright, whatever the story. Matched case-insensitively
# as whole words against the article's publisher name and its URLs, so "msn"
# catches the "MSN" publisher and the msn.com domain but not a stray "msn"
# substring inside a base64 Google News link. Aggregators like MSN routinely
# republish long-concluded stories under a refreshed date, defeating the
# 1-day freshness window - so we never ingest them in the first place.
SOURCE_BLOCKLIST = [
    "MSN",
    # mshale.com, blocked 2026-08-16. Reaches us through Google News under the
    # publisher name "Mshale", serving Arabic football copy on random-hash paths
    # (/1268f21f/5c02935c72SMJJT0jbM) - a scraper domain, not a newsroom. Its
    # three ingested items were all stale rehashes or fabricated, and the hash
    # paths mean no stable URL to date-check against. "mshale" also matches the
    # domain on the post-resolution pass if the publisher name ever changes.
    "Mshale",
]

# Hard ceiling on article age, enforced against the date printed on the
# article page itself (extracted alongside the content). The feed-reported
# date is not trusted on its own: Google News and aggregators re-serve
# long-concluded stories under refreshed timestamps, which is how a May
# title-decider passed the 1-day window in July.
MAX_ARTICLE_AGE_DAYS = 3

# RSS feed sources - this list is what the RSS collector actually fetches;
# add/remove feeds here
#
# Nessma TV's two feeds (/ar/rss/news/27, /fr/rss/news/4) were removed on
# 2026-07-25: Cloudflare 403s them from GitHub runner IPs on every single
# run (~200 ERROR lines/day) while returning 200 to a residential IP with
# the collector's own browser User-Agent, so no header change fixes it. They
# had not yielded an article since 2025-11-20. Nessma stories still reach
# us through Google News under the source name "Nessma TV".
RSS_FEEDS = [
    # Tunisian news (French)
    {
        "name": "Mosaique FM (TN)",
        "url": "https://www.mosaiquefm.net/fr/rss",
        "language": "fr"
    },
]

# Content extraction
EXTRACTION_TIMEOUT = 10  # seconds
MIN_ARTICLE_LENGTH = 100  # characters - shorter extractions are discarded

# Publisher circuit breaker. When a publisher's origin goes down, every URL
# it appears in costs a full EXTRACTION_TIMEOUT and fails identically, run
# after run: mosaiquefm.net 503'd behind Cloudflare from 2026-08-01 17:15Z
# and produced 38 dead fetches over the next 19 hours, ~4 minutes of run
# time spent waiting on a host we already knew was down. After this many
# consecutive failures the domain is skipped entirely until the cooldown
# lapses, then one URL is let through as a probe - if it fails, the streak
# grows and the domain closes again for another cooldown. A single success
# clears the streak. Skipped URLs behave exactly like failed extractions
# (title-only, held by the existing guards), so nothing is buried by this.
EXTRACTION_CIRCUIT_TRIP = 5
EXTRACTION_CIRCUIT_COOLDOWN_HOURS = 3

# Repeat "extraction degraded" alerts for a publisher we have already
# reported are noise: the Mosaique outage above fired 15 identical pings.
# A domain already alerted about stays quiet for this long. The suppression
# is per domain, never global - a second publisher failing still pages
# immediately instead of hiding behind the first one's outage.
EXTRACTION_ALERT_COOLDOWN_HOURS = 12

# Full article text is blanked after this many days (summaries and metadata
# are kept forever) to cap the growth of the git-committed database. Note:
# no VACUUM - rewriting the whole file would defeat git's delta compression.
CONTENT_RETENTION_DAYS = 30

# Cadence watchdog. The punctual every-15-minutes trigger is cron-job.org
# firing workflow_dispatch - external, deliberate, and invisible from this
# repo. The workflow's own cron is the failover, but GitHub runs scheduled
# jobs best-effort: measured over 22h on 2026-07-25 it fired 13 of ~88 slots
# (15%), against 87 dispatches from cron-job.org. So if the external trigger
# ever stops, collection does not fail - it silently drops to roughly one run
# every 100 minutes, and the only symptom is a channel that feels slow.
# A run that starts more than this many minutes after the previous one pings
# the ops chat. 45 leaves room for a skipped slot plus a slow run without
# crying wolf. During a real outage the surviving cron runs keep re-alerting
# every ~100 minutes; that repetition is intended, not a misfire.
RUN_GAP_ALERT_MINUTES = 45

# Heartbeat rows are one per run (~200/day) in a database that is committed
# to git on every run, so they are pruned on the same pass as article text.
# A week is enough to answer "how often did we actually run?" after the fact.
RUN_HEARTBEAT_RETENTION_DAYS = 7

# Classification categories
CATEGORIES = {
    "match": {
        "name_fr": "Résultats de match",
        "name_ar": "نتائج المباريات",
        "name_en": "Match Results",
        "emoji": "⚽",
        "keywords": [
            "match", "victoire", "défaite", "nul", "score", "but", "goal",
            "win", "loss", "draw", "victory", "مباراة", "فوز", "هزيمة", "تعادل"
        ]
    },
    "transfer": {
        "name_fr": "Mercato & Transferts",
        "name_ar": "الانتقالات",
        "name_en": "Transfers & Mercato",
        "emoji": "💼",
        "keywords": [
            "transfert", "mercato", "recrutement", "signer", "contrat", "recruter",
            "transfer", "signing", "contract", "انتقال", "عقد", "تعاقد"
        ]
    },
    "injury": {
        "name_fr": "Blessures",
        "name_ar": "الإصابات",
        "name_en": "Injuries",
        "emoji": "🏥",
        "keywords": [
            "blessure", "blessé", "absent", "indisponible", "forfait",
            "injury", "injured", "unavailable", "إصابة", "مصاب", "غياب"
        ]
    },
    "statement": {
        "name_fr": "Déclarations",
        "name_ar": "التصريحات",
        "name_en": "Statements",
        "emoji": "💬",
        "keywords": [
            "déclaration", "interview", "conférence de presse",
            "statement", "press conference", "تصريح", "مؤتمر صحفي"
        ]
    },
    "finance": {
        "name_fr": "Finances & Gestion",
        "name_ar": "المالية",
        "name_en": "Finance & Management",
        "emoji": "💰",
        "keywords": [
            "dette", "budget", "sponsor", "contrat", "finances", "salaire",
            "debt", "budget", "salary", "ديون", "ميزانية", "راتب"
        ]
    },
    "other": {
        "name_fr": "Autres actualités",
        "name_ar": "أخبار أخرى",
        "name_en": "Other News",
        "emoji": "📰",
        "keywords": []
    }
}

# API Keys (loaded from environment variables)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini API settings
# Free-tier quotas verified LIVE on 2026-07-18 (429 quotaValue + probe calls,
# do not trust remembered numbers): each model has its OWN daily bucket of
# ~20 requests/day, refilled gradually through the day - not the ~250/day
# this design originally assumed (Google cut free tiers in Dec 2025;
# gemini-2.5-flash-lite is closed to new projects, 2.0-* buckets are zero).
# Processing therefore tries these models in order and moves to the next on
# a quota error, giving several independent daily buckets. Order = newest/
# best first.
GEMINI_MODELS = [
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
]

# A flaky AI "irrelevant" verdict must not blacklist a fresh URL forever
# (2026-07-18: a legit "Diarra signs for EST" story was lost this way).
# 'irrelevant' and 'unverified_date' rejections (one stochastic AI call /
# one publisher-feed snapshot) are re-judged after this many hours; stale/
# duplicate/already_covered rejections stay permanent - re-judging can't
# change those.
IRRELEVANT_REJECTION_TTL_HOURS = 6

# 'already_covered' looks like a durable fact but is really two judgments
# glued together: "same story as one we ran" (durable - a re-run cannot
# change it) and "and it adds nothing new" (stochastic, exactly as fallible
# as 'irrelevant'). The second half buried "L'EST renonce au recrutement
# Seydou Lamine Sacko" on 2026-07-22 - the cancellation of a signing we had
# already announced to fans - permanently, on one model call. Let these
# expire too, so a misjudged story gets a second reading while it is still
# news. Set to UPDATE_COOLDOWN_HOURS: an item comes back up for judgment at
# roughly the moment its story is eligible to be updated again, so the
# re-read can actually change the outcome instead of being re-suppressed.
ALREADY_COVERED_REJECTION_TTL_HOURS = 12

# A running saga (mercato especially) produces a fresh "decisive" angle every
# few hours, and each one clears any materiality bar the model is given: the
# Tougaï->Al Ahli story alone spawned 8 near-identical "Mise à jour" posts
# over 2026-07-19..21. Rather than tighten the bar until updates stop
# entirely (which is what happened next - 07-22 published 2 posts, 0 updates,
# while 39 items were buried as already-covered), cap the *rate*: at most one
# update per story per this many hours. Materiality still decides whether an
# item is an update at all; this only decides how often one may land.
UPDATE_COOLDOWN_HOURS = 12

# Telegram settings
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
