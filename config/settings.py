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
]

# Hard ceiling on article age, enforced against the date printed on the
# article page itself (extracted alongside the content). The feed-reported
# date is not trusted on its own: Google News and aggregators re-serve
# long-concluded stories under refreshed timestamps, which is how a May
# title-decider passed the 1-day window in July.
MAX_ARTICLE_AGE_DAYS = 3

# RSS feed sources - this list is what the RSS collector actually fetches;
# add/remove feeds here
RSS_FEEDS = [
    # Tunisian news (Arabic)
    {
        "name": "Nessma TV Sport (TN)",
        "url": "https://www.nessma.tv/ar/rss/news/27",
        "language": "ar"
    },
    # Tunisian news (French)
    {
        "name": "Nessma TV Sport (TN)",
        "url": "https://www.nessma.tv/fr/rss/news/4",
        "language": "fr"
    },
    {
        "name": "Mosaique FM (TN)",
        "url": "https://www.mosaiquefm.net/fr/rss",
        "language": "fr"
    },
]

# Content extraction
EXTRACTION_TIMEOUT = 10  # seconds
MIN_ARTICLE_LENGTH = 100  # characters - shorter extractions are discarded

# Full article text is blanked after this many days (summaries and metadata
# are kept forever) to cap the growth of the git-committed database. Note:
# no VACUUM - rewriting the whole file would defeat git's delta compression.
CONTENT_RETENTION_DAYS = 30

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
