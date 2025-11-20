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

# Collection settings
COLLECTION_INTERVAL_MINUTES = 30
MAX_ARTICLES_PER_SOURCE = 100
ARTICLE_RETENTION_DAYS = 90  # Keep articles for 3 months

# Google News settings
# Note: These settings affect ranking/prioritization, NOT which languages are searched
# The actual language of results depends on your search queries (we use French, Arabic, English)
GNEWS_LANGUAGE = "en"  # Interface language (doesn't restrict search results)
GNEWS_COUNTRY = "TN"   # Tunisia - prioritizes Tunisian news sources
GNEWS_PERIOD = "7d"    # Last 7 days (was "1h" - too short for testing)
GNEWS_MAX_RESULTS = 100  # Max results per query

# RSS Feed sources
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

# Twitter settings
TWITTER_MAX_TWEETS = 100
TWITTER_LOOKBACK_HOURS = 1

# Content extraction
EXTRACTION_TIMEOUT = 10  # seconds
MIN_ARTICLE_LENGTH = 100  # characters

# Deduplication
SIMILARITY_THRESHOLD = 0.85  # 85% similarity = duplicate
TIME_WINDOW_HOURS = 24       # Consider articles within 24h for deduplication

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
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini API settings
GEMINI_MODEL = "gemini-pro"
GEMINI_MAX_REQUESTS_PER_DAY = 1500
GEMINI_REQUESTS_PER_MINUTE = 15

# Telegram settings
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
DIGEST_TIME_UTC = "08:00"  # 8 AM UTC

# Error notifications
NOTIFY_ON_ERROR = True
ALERT_THRESHOLD_NO_ARTICLES = 5  # Alert if less than 5 articles collected

# Database cleanup
CLEANUP_OLDER_THAN_DAYS = 90
VACUUM_DATABASE = True
