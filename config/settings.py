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
# One batched request per collection run keeps usage well below the
# free-tier daily quota (~250 requests/day for gemini-2.5-flash in 2026).
GEMINI_MODEL = "gemini-2.5-flash"

# Telegram settings
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
