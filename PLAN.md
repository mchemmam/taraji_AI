# Taraji AI - Complete System Design & Implementation Plan

**News Monitoring System for Espérance Sportive de Tunis**

**Deployment:** Oracle Cloud Free Tier (Always Free)
**Cost:** $0/month forever
**Timeline:** 2-3 weeks for full implementation
**Last Updated:** 2025-11-19

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Oracle Cloud Setup Guide](#oracle-cloud-setup-guide)
5. [Data Collection Strategy](#data-collection-strategy)
6. [Processing Pipeline](#processing-pipeline)
7. [Storage Design](#storage-design)
8. [Distribution Channels](#distribution-channels)
9. [Project Structure](#project-structure)
10. [Implementation Roadmap](#implementation-roadmap)
11. [Deployment Guide](#deployment-guide)
12. [Monitoring & Maintenance](#monitoring--maintenance)
13. [Risks & Mitigation](#risks--mitigation)
14. [Future Enhancements](#future-enhancements)

---

## System Overview

### Goal
Automatically monitor the internet for any mention of "Esperance Sportive de Tunis" across all relevant sources in all languages (French, Arabic, English, etc.), filter relevant news, classify content, and distribute summaries via Telegram and other channels.

### Key Features
- Multi-source monitoring (Google News, Twitter, RSS feeds)
- Multi-language support (French, Arabic, English, Spanish, etc.)
- Intelligent deduplication across languages
- AI-powered summarization
- Automatic classification (transfers, matches, injuries, etc.)
- Daily digest distribution to Telegram
- Optional: Web dashboard for browsing archive

### Constraints
- 100% free (no monthly costs)
- Self-hosted on Oracle Cloud Free Tier
- Open-source tools only
- Privacy-focused (no external paid services)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORACLE CLOUD FREE TIER VM                     │
│                    (ARM Instance: 4 cores, 24GB RAM)             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              DATA COLLECTION LAYER                       │   │
│  │  • Google News Collector (gnews)                        │   │
│  │  • Twitter Collector (snscrape/nitter)                  │   │
│  │  • RSS Feed Aggregator (feedparser)                     │   │
│  │  • Custom Web Scrapers (BeautifulSoup)                  │   │
│  └──────────────────┬──────────────────────────────────────┘   │
│                     │                                            │
│                     ▼                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              PROCESSING PIPELINE                         │   │
│  │  1. Raw Data Ingestion → JSON storage                   │   │
│  │  2. Language Detection (langdetect/fasttext)            │   │
│  │  3. Content Extraction (newspaper3k/trafilatura)        │   │
│  │  4. Keyword Matching & Filtering (rapidfuzz)            │   │
│  │  5. Deduplication (TF-IDF + cosine similarity)          │   │
│  │  6. Classification (rule-based → ML later)              │   │
│  │  7. Summarization (Google Gemini API)                   │   │
│  └──────────────────┬──────────────────────────────────────┘   │
│                     │                                            │
│                     ▼                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              STORAGE LAYER                               │   │
│  │  • SQLite Database (structured data)                    │   │
│  │  • JSON Files (raw data backup)                         │   │
│  │  • File System (logs, artifacts)                        │   │
│  └──────────────────┬──────────────────────────────────────┘   │
│                     │                                            │
│                     ▼                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              DISTRIBUTION LAYER                          │   │
│  │  • Telegram Bot API (daily digest + commands)           │   │
│  │  • Optional: Streamlit Dashboard (web UI)               │   │
│  │  • Optional: Facebook/Twitter posting                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              SCHEDULER                                   │   │
│  │  • Cron jobs (every 30 minutes for collection)          │   │
│  │  • Daily digest (8:00 AM UTC)                           │   │
│  │  • Weekly cleanup (Sunday midnight)                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Core Technologies
```
Language:        Python 3.11+
Database:        SQLite (upgrade to PostgreSQL if needed)
Web Framework:   Streamlit (dashboard - optional)
Scheduler:       Cron (built-in Linux)
Deployment:      Oracle Cloud Always Free VM
OS:              Ubuntu 22.04 LTS (ARM64)
```

### Python Libraries (All Free)

```txt
# Data Collection
gnews==0.3.7                    # Google News (no API key)
snscrape                        # Twitter scraping (no API key)
feedparser==6.0.10              # RSS feed parser
requests==2.31.0                # HTTP client
beautifulsoup4==4.12.0          # HTML parsing
newspaper3k==0.2.8              # Article extraction
trafilatura==1.6.2              # Alternative article extraction

# NLP & Text Processing
langdetect==1.0.9               # Language detection
rapidfuzz==3.5.2                # Fuzzy string matching (typo tolerance)
scikit-learn==1.4.0             # ML tools, TF-IDF, clustering
nltk==3.8.1                     # Natural language processing
sumy==0.11.0                    # Extractive summarization (fallback)

# AI/LLM
google-generativeai==0.3.2      # Google Gemini API (free tier)

# Database
sqlite3                         # Built-in with Python
sqlalchemy==2.0.25              # ORM (optional, for easier queries)

# Distribution
python-telegram-bot==20.7       # Telegram Bot API
streamlit==1.31.0               # Web dashboard (optional)

# Utilities
python-dotenv==1.0.0            # Environment variables
schedule==1.2.0                 # Alternative to cron (if needed)
loguru==0.7.2                   # Beautiful logging
python-dateutil==2.8.2          # Date parsing
pytz==2024.1                    # Timezone handling
```

### External Services (All Free Tier)

| Service | Purpose | Free Tier Limits | Cost |
|---------|---------|------------------|------|
| Oracle Cloud | Hosting VM | 4 ARM cores, 24GB RAM, 200GB storage | $0 forever |
| Google Gemini API | AI summarization | 1,500 requests/day, 15/min | $0 |
| Telegram Bot API | Message distribution | Unlimited | $0 |
| Google News | News aggregation | No documented limits | $0 |
| Nitter instances | Twitter scraping proxy | Varies by instance | $0 |

---

## Oracle Cloud Setup Guide

### Step 1: Create Oracle Cloud Account

1. Go to https://www.oracle.com/cloud/free/
2. Click "Start for free"
3. Fill in your details (requires email, phone, credit card for verification)
   - **Note:** Credit card is for identity verification only - won't be charged
4. Verify your email and phone
5. Complete account setup

### Step 2: Create VM Instance

1. Log in to Oracle Cloud Console
2. Click "Create a VM instance"
3. Configure your instance:

**Name:** `taraji-ai-vm`

**Image:** `Canonical Ubuntu 22.04 (ARM64)`

**Shape:**
- Click "Change Shape"
- Select "Ampere" (ARM-based)
- Choose: `VM.Standard.A1.Flex`
- **OCPUs:** 4 (use all available free tier)
- **Memory:** 24 GB (use all available free tier)

**Network:**
- Create new VCN (Virtual Cloud Network) - use defaults
- Assign public IP: Yes

**SSH Keys:**
- Generate new key pair and download both:
  - `taraji-ai-vm.key` (private key - keep safe!)
  - `taraji-ai-vm.key.pub` (public key)

4. Click "Create"
5. Wait 2-3 minutes for provisioning

### Step 3: Configure Firewall

1. In VM details page, click on the subnet link
2. Click on the default security list
3. Add ingress rules:
   - **For SSH:** Allow port 22 from your IP (already there)
   - **For Streamlit (optional):** Allow port 8501 from 0.0.0.0/0
4. Also configure Ubuntu firewall (we'll do this after SSH)

### Step 4: Connect to VM

**On Linux/Mac:**
```bash
chmod 600 ~/Downloads/taraji-ai-vm.key
ssh -i ~/Downloads/taraji-ai-vm.key ubuntu@<PUBLIC_IP>
```

**On Windows:**
- Use PuTTY with the private key converted to .ppk format
- Or use Windows Subsystem for Linux (WSL) with the command above

Replace `<PUBLIC_IP>` with the public IP shown in your VM details.

### Step 5: Initial VM Setup

Once connected via SSH:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
sudo apt install python3.11 python3.11-venv python3-pip git -y

# Install system dependencies
sudo apt install build-essential libssl-dev libffi-dev python3-dev -y

# Configure firewall (allow SSH and optionally Streamlit)
sudo ufw allow 22/tcp
sudo ufw allow 8501/tcp  # Optional: for Streamlit dashboard
sudo ufw enable

# Set timezone (adjust to your preference)
sudo timedatectl set-timezone Africa/Tunis

# Verify installation
python3.11 --version
git --version
```

### Step 6: Create Project Directory

```bash
# Create application directory
mkdir -p ~/taraji_ai
cd ~/taraji_ai

# Initialize git repository (optional, for version control)
git init
```

Your Oracle Cloud VM is now ready for deployment!

---

## Data Collection Strategy

### Sources & Methods

#### 1. Google News
**Library:** `gnews`
**Frequency:** Every 30 minutes
**Languages:** All (fr, ar, en, es, etc.)

**Keywords to search:**
```python
SEARCH_QUERIES = [
    "Espérance Sportive de Tunis",
    "Esperance Sportive de Tunis",
    "Espérance Tunis",
    "Esperance Tunis",
    "EST Tunis",
    "Taraji",
    "الترجي الرياضي التونسي",
    "الترجي التونسي",
    "الترجي",
]
```

**Implementation:**
```python
from gnews import GNews

def collect_google_news():
    news = GNews(language='fr', country='TN', period='1h', max_results=100)
    articles = []
    for query in SEARCH_QUERIES:
        results = news.get_news(query)
        articles.extend(results)
    return articles
```

**Expected yield:** 10-30 articles per hour

#### 2. Twitter/X
**Library:** `snscrape` (primary) or Nitter scraping (fallback)
**Frequency:** Every 30 minutes
**Search strategy:** Recent tweets (last hour)

**Keywords:**
```python
TWITTER_QUERIES = [
    "Espérance Tunis",
    "Esperance Tunis",
    "EST",
    "#Taraji",
    "الترجي",
]
```

**Implementation (snscrape):**
```python
import snscrape.modules.twitter as sntwitter

def collect_tweets():
    tweets = []
    for query in TWITTER_QUERIES:
        search = f"{query} lang:fr OR lang:ar OR lang:en since_time:1h"
        for tweet in sntwitter.TwitterSearchScraper(search).get_items():
            if len(tweets) >= 100:
                break
            tweets.append({
                'url': tweet.url,
                'content': tweet.content,
                'date': tweet.date,
                'user': tweet.user.username,
                'retweets': tweet.retweetCount,
                'likes': tweet.likeCount,
            })
    return tweets
```

**Fallback (Nitter scraping):**
If snscrape breaks, scrape from `nitter.net` instead of `twitter.com`

**Expected yield:** 20-50 tweets per hour

#### 3. RSS Feeds
**Library:** `feedparser`
**Frequency:** Every 30 minutes
**Sources:** Curated list of sports news sites

**RSS Feed List:**
```python
RSS_FEEDS = [
    # International sports
    'https://www.espn.com/espn/rss/soccer/news',
    'https://www.goal.com/feeds/en/news',

    # French sports
    'https://www.lequipe.fr/rss/actu_rss.xml',
    'https://www.footmercato.net/rss.php',

    # Tunisian news
    'https://www.babnet.net/rss/sport.xml',
    'https://www.mosaiquefm.net/fr/rss/sport',
    'https://www.alchourouk.com/rss/sport',

    # African football
    'https://www.cafonline.com/rss',

    # Add 10-15 more relevant feeds
]
```

**Implementation:**
```python
import feedparser

def collect_rss():
    articles = []
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            articles.append({
                'title': entry.title,
                'url': entry.link,
                'published': entry.published,
                'summary': entry.get('summary', ''),
                'source': feed.feed.title,
            })
    return articles
```

**Expected yield:** 50-100 articles per hour (most irrelevant, filtered out)

#### 4. Custom Web Scrapers (Future)
For specific sites without RSS/API:
- Tunisian sports forums
- Club official website
- Facebook public pages (via RSS Bridge)

---

## Processing Pipeline

### Step 1: Raw Data Ingestion

**Input:** Articles/tweets from collectors
**Output:** Saved to `data/raw/{source}/{timestamp}.json`

```python
def ingest_raw_data(articles, source):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = f"data/raw/{source}/{timestamp}.json"

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    return filepath
```

### Step 2: Language Detection

**Library:** `langdetect`
**Purpose:** Identify article language for later processing

```python
from langdetect import detect, LangDetectException

def detect_language(text):
    try:
        return detect(text)
    except LangDetectException:
        return 'unknown'
```

**Supported languages:** fr, ar, en, es, de, it, pt, etc.

### Step 3: Content Extraction & Cleaning

**Library:** `newspaper3k` or `trafilatura`
**Purpose:** Extract clean article text from URLs

```python
from newspaper import Article

def extract_content(url):
    try:
        article = Article(url)
        article.download()
        article.parse()

        return {
            'title': article.title,
            'text': article.text,
            'authors': article.authors,
            'publish_date': article.publish_date,
            'top_image': article.top_image,
        }
    except Exception as e:
        logger.error(f"Failed to extract {url}: {e}")
        return None
```

### Step 4: Keyword Matching & Filtering

**Challenge:** Detect club mentions with typo tolerance and transliteration variants

**Strategy:**
1. Exact keyword match (fast, catches 80%)
2. Fuzzy matching for typos (slower, catches remaining 15%)
3. Contextual verification (prevent false positives)

**Keywords database:**
```python
KEYWORDS = {
    'exact': {
        'fr': [
            'Espérance Sportive de Tunis',
            'Esperance Sportive de Tunis',
            'Espérance de Tunis',
            'Esperance de Tunis',
            'Espérance Tunis',
            'Esperance Tunis',
            'EST Tunis',  # Only with "Tunis" to avoid false positives
            'Taraji',     # Arabic transliteration
        ],
        'ar': [
            'الترجي الرياضي التونسي',
            'الترجي التونسي',
            'الترجي',
        ],
        'en': [
            'Esperance Sportive de Tunis',
            'Esperance of Tunis',
            'Esperance Tunis',
            'EST Tunis',
        ],
    },
    'contextual': {
        # These require additional context words nearby to avoid false positives
        'EST': ['Tunis', 'Tunisia', 'Tunisie', 'football', 'CAF', 'الترجي'],
        'Taraji': ['Tunisia', 'Tunis', 'Tunisie', 'football', 'الترجي'],
    },
    'negative': [
        # Exclude other clubs with similar names
        'Espérance de Zarzis',
        'Esperance de Zarzis',
        'Espérance du Sahel',
        'Esperance du Sahel',
        'ES Sahel',
        'ESS',
        # Exclude celebrity with similar name
        'Taraji P. Henson',
        'Taraji Henson',
        'Taraji P Henson',
        'actress Taraji',
    ]
}
```

**Implementation:**
```python
from rapidfuzz import fuzz

def matches_keywords(text, language='unknown'):
    text_lower = text.lower()

    # Check negative keywords first (highest priority)
    for neg_keyword in KEYWORDS['negative']:
        if neg_keyword.lower() in text_lower:
            return False

    # Check exact matches
    keywords = KEYWORDS['exact'].get(language, [])
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return True

    # Check all languages if language unknown
    if language == 'unknown':
        for lang_keywords in KEYWORDS['exact'].values():
            for keyword in lang_keywords:
                if keyword.lower() in text_lower:
                    return True

    # Check contextual keywords (require context words nearby)
    for keyword, context_words in KEYWORDS['contextual'].items():
        if keyword.lower() in text_lower:
            # Check if any context word appears in the text
            for context in context_words:
                if context.lower() in text_lower:
                    return True

    # Fuzzy matching for typos (threshold 85%)
    # Only for main club name variations to avoid false positives
    main_keywords = [
        'Espérance Sportive de Tunis',
        'Esperance Sportive de Tunis',
        'الترجي الرياضي التونسي',
    ]
    for keyword in main_keywords:
        if fuzz.partial_ratio(keyword.lower(), text_lower) > 85:
            return True

    return False
```

### Step 5: Deduplication

**Challenge:** Same story appears in multiple sources and languages

**Strategy:** Multi-signal similarity detection

**Signals:**
1. **Exact URL match** (trivial)
2. **Title similarity** (TF-IDF + cosine similarity)
3. **Content similarity** (first 500 chars)
4. **Time window** (within 24 hours)

**Implementation:**
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class Deduplicator:
    def __init__(self, threshold=0.85):
        self.threshold = threshold
        self.vectorizer = TfidfVectorizer()

    def find_duplicates(self, articles):
        # Group by 24-hour windows
        grouped = self._group_by_time(articles)

        duplicates = []
        for group in grouped:
            # Vectorize titles
            titles = [a['title'] for a in group]
            vectors = self.vectorizer.fit_transform(titles)

            # Calculate pairwise similarity
            similarity = cosine_similarity(vectors)

            # Find pairs above threshold
            for i in range(len(group)):
                for j in range(i+1, len(group)):
                    if similarity[i][j] > self.threshold:
                        duplicates.append((group[i], group[j]))

        return duplicates

    def _group_by_time(self, articles):
        # Group articles within 24-hour windows
        # Implementation details...
        pass
```

**Deduplication logic:**
- Keep the first article found
- Mark duplicates with `duplicate_of` field pointing to original
- Store all URLs (don't delete duplicates - useful for tracking spread)

### Step 6: Classification

**Categories:**
```python
CATEGORIES = {
    'match': {
        'name_fr': 'Résultats de match',
        'name_ar': 'نتائج المباريات',
        'emoji': '⚽',
        'keywords': ['match', 'victoire', 'défaite', 'nul', 'score', 'but', 'goal', 'win', 'loss', 'draw']
    },
    'transfer': {
        'name_fr': 'Mercato & Transferts',
        'name_ar': 'الانتقالات',
        'emoji': '💼',
        'keywords': ['transfert', 'mercato', 'recrutement', 'signer', 'contrat', 'recruter', 'انتقال']
    },
    'injury': {
        'name_fr': 'Blessures',
        'name_ar': 'الإصابات',
        'emoji': '🏥',
        'keywords': ['blessure', 'blessé', 'absent', 'indisponible', 'forfait', 'injury', 'injured']
    },
    'statement': {
        'name_fr': 'Déclarations',
        'name_ar': 'التصريحات',
        'emoji': '💬',
        'keywords': ['déclaration', 'interview', 'conférence de presse', 'تصريح']
    },
    'finance': {
        'name_fr': 'Finances & Gestion',
        'name_ar': 'المالية',
        'emoji': '💰',
        'keywords': ['dette', 'budget', 'sponsor', 'contrat', 'finances', 'salaire']
    },
    'other': {
        'name_fr': 'Autres actualités',
        'name_ar': 'أخبار أخرى',
        'emoji': '📰',
        'keywords': []
    }
}
```

**Implementation (Rule-based):**
```python
def classify_article(title, content):
    text = (title + ' ' + content).lower()

    scores = {}
    for category, data in CATEGORIES.items():
        if category == 'other':
            continue

        score = 0
        for keyword in data['keywords']:
            if keyword.lower() in text:
                score += 1

        scores[category] = score

    # Return category with highest score, or 'other' if all zero
    if max(scores.values()) == 0:
        return 'other'

    return max(scores, key=scores.get)
```

**Future improvement:** Train ML classifier (Logistic Regression or Naive Bayes) once we have 100+ labeled articles per category

### Step 7: Summarization

**Strategy:** Use Google Gemini API (free tier: 1,500 requests/day)

**Prompt template:**
```python
SUMMARIZATION_PROMPT = """
Résumé cet article de sport en français en 2-3 phrases maximum.
Concentre-toi sur les faits importants concernant l'Espérance Sportive de Tunis.

Article: {title}

Contenu: {content}

Résumé:
"""
```

**Implementation:**
```python
import google.generativeai as genai

class Summarizer:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def summarize(self, title, content, language='fr'):
        prompt = self._build_prompt(title, content, language)

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            # Fallback to extractive summarization
            return self._extractive_summary(content)

    def _extractive_summary(self, content):
        # Simple fallback: return first 2 sentences
        sentences = content.split('.')[:2]
        return '. '.join(sentences) + '.'
```

**Rate limiting:**
- Max 1,500 requests/day
- If we collect 50 articles/day → well within limits
- Implement exponential backoff for API errors

---

## Storage Design

### Database Schema (SQLite)

```sql
-- Main articles table
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    source_type TEXT,  -- 'google_news', 'twitter', 'rss'
    published_date DATETIME,
    collected_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    language TEXT,
    category TEXT,
    content TEXT,
    summary TEXT,
    duplicate_of INTEGER,
    is_published BOOLEAN DEFAULT 0,

    -- Metadata
    author TEXT,
    image_url TEXT,

    -- Twitter-specific
    retweets INTEGER,
    likes INTEGER,

    FOREIGN KEY (duplicate_of) REFERENCES articles(id)
);

-- Indexes for performance
CREATE INDEX idx_published_date ON articles(published_date DESC);
CREATE INDEX idx_category ON articles(category);
CREATE INDEX idx_language ON articles(language);
CREATE INDEX idx_collected_date ON articles(collected_date DESC);
CREATE INDEX idx_is_published ON articles(is_published);

-- Keywords matched (for analytics)
CREATE TABLE keywords_matched (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    match_type TEXT,  -- 'exact', 'fuzzy'
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);

CREATE INDEX idx_keywords_article ON keywords_matched(article_id);

-- Collection statistics (for monitoring)
CREATE TABLE collection_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    source TEXT NOT NULL,
    articles_collected INTEGER,
    articles_filtered INTEGER,  -- passed keyword filter
    articles_stored INTEGER,  -- not duplicates
    errors INTEGER,
    duration_seconds REAL
);

-- Distribution log (track what was sent)
CREATE TABLE distribution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    channel TEXT NOT NULL,  -- 'telegram', 'facebook', 'twitter'
    sent_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    message_id TEXT,
    status TEXT,  -- 'success', 'failed'
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);
```

### File System Structure

```
~/taraji_ai/
├── data/
│   ├── taraji_ai.db              # SQLite database
│   ├── raw/                      # Raw JSON backups
│   │   ├── google_news/
│   │   │   └── 20250119_120000.json
│   │   ├── twitter/
│   │   │   └── 20250119_120000.json
│   │   └── rss/
│   │       └── 20250119_120000.json
│   └── exports/                  # Weekly exports for backup
│       └── articles_20250119.json
├── logs/
│   ├── app.log                   # Application logs
│   ├── errors.log                # Error logs
│   └── cron.log                  # Cron job logs
└── temp/                         # Temporary files
    └── .gitkeep
```

### Backup Strategy

**Daily:**
- SQLite auto-commits after each run
- Raw JSON files kept for 7 days

**Weekly:**
- Full database export to JSON: `data/exports/articles_YYYYMMDD.json`
- Compressed backup: `tar -czf backup_YYYYMMDD.tar.gz data/`
- Keep last 4 weeks of backups

**Monthly:**
- Optional: Upload backup to Google Drive (via rclone - free)

---

## Distribution Channels

### Telegram Bot & Channel

**Setup:**
1. Create bot via @BotFather on Telegram
2. Get bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
3. Create channel (e.g., @taraji_news)
4. Add bot as admin to channel

**Features:**

**1. Daily Digest (automatic at 8 AM)**
```
📰 Taraji News - 19 Janvier 2025

⚽ Résultats de match (2)
• L'EST bat le CA 2-1 en match amical - L'Équipe
• Victoire importante avant la Ligue des Champions - Goal

💼 Mercato & Transferts (3)
• L'EST proche de recruter un attaquant brésilien - Foot Mercato
• Négociations avancées avec Zamalek pour... - Mosaique FM
• Le club cible deux joueurs argentins - Babnet

🏥 Blessures (1)
• Mohamed Ali Ben Romdhane forfait pour 3 semaines - Alchourouk

💬 Déclarations (1)
• L'entraîneur confiant avant le match crucial - JeuneAfrique

Total: 7 nouvelles aujourd'hui
📊 Archive complète: https://taraji-ai.yourdomain.com
```

**2. Bot Commands (for personal queries)**
```
/latest - Last 5 articles
/today - All articles today
/category [name] - Articles by category
/search [keyword] - Search articles
/stats - Collection statistics
```

**Implementation:**
```python
from telegram import Bot
from telegram.constants import ParseMode

async def send_daily_digest(bot_token, channel_id):
    bot = Bot(token=bot_token)

    # Fetch articles from last 24 hours
    articles = get_articles_last_24h()

    # Group by category
    by_category = group_by_category(articles)

    # Format message
    message = format_digest(by_category)

    # Send to channel
    await bot.send_message(
        chat_id=channel_id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )
```

### Web Dashboard (Optional - Streamlit)

**Features:**
- Browse all articles (filterable by date, category, language)
- Search functionality
- View duplicates grouped together
- Statistics & charts (articles per day, category distribution)
- Manual moderation (approve/reject for social media posting)

**Deployment:**
- Run on Oracle Cloud VM: `streamlit run dashboard/app.py --server.port 8501`
- Access via: `http://<VM_PUBLIC_IP>:8501`
- Optional: Set up domain name + nginx reverse proxy for HTTPS

**Simple implementation:**
```python
import streamlit as st
import pandas as pd
import sqlite3

st.title("📰 Taraji AI - News Archive")

# Connect to database
conn = sqlite3.connect('data/taraji_ai.db')

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    category = st.selectbox("Category", ["All"] + list(CATEGORIES.keys()))
with col2:
    language = st.selectbox("Language", ["All", "fr", "ar", "en"])
with col3:
    days = st.slider("Last N days", 1, 30, 7)

# Query database
query = """
    SELECT title, source, published_date, category, summary, url
    FROM articles
    WHERE collected_date >= date('now', '-{} days')
    AND duplicate_of IS NULL
""".format(days)

if category != "All":
    query += f" AND category = '{category}'"
if language != "All":
    query += f" AND language = '{language}'"

query += " ORDER BY published_date DESC"

df = pd.read_sql_query(query, conn)

# Display
st.write(f"Found {len(df)} articles")
for _, row in df.iterrows():
    with st.expander(f"{row['category']} - {row['title']}"):
        st.write(f"**Source:** {row['source']}")
        st.write(f"**Date:** {row['published_date']}")
        st.write(f"**Summary:** {row['summary']}")
        st.write(f"[Read more]({row['url']})")
```

### Facebook & Twitter (Future)

**Facebook:** (parked idea, 2026-07-16 — not yet implemented)
- New distributor module (`distributors/facebook_page.py`), same pattern as `telegram_bot.py`: plain HTTPS calls to the Graph API, no SDK
- `POST /{page-id}/feed` with the article title/summary/link
- Auth: a **long-lived Page Access Token**, generated once via Graph API Explorer (never expires in practice)
- Since we'd only post to our own Page, **no Facebook App Review needed** — that's only required if other users' Pages are involved
- Setup is heavier than Telegram's (need a Facebook Developer app + the token exchange flow), but posting itself is a single HTTP call, fits the existing GitHub Actions step

**Twitter:**
- Use Twitter API (free tier: 50 tweets/month)
- Post only major news due to limits
- Alternative: Use unofficial libraries (risky)

**Recommendation:** Start with Telegram only, add social media in Phase 4

---

## Project Structure

```
taraji_ai/
├── collectors/
│   ├── __init__.py
│   ├── base_collector.py         # Base class for all collectors
│   ├── google_news.py             # Google News collector
│   ├── twitter_collector.py       # Twitter/X collector
│   └── rss_collector.py           # RSS feed collector
│
├── processors/
│   ├── __init__.py
│   ├── language_detector.py       # Language detection
│   ├── keyword_filter.py          # Keyword matching & filtering
│   ├── deduplicator.py            # Duplicate detection
│   ├── classifier.py              # Category classification
│   ├── summarizer.py              # AI summarization
│   └── content_extractor.py       # Article text extraction
│
├── storage/
│   ├── __init__.py
│   ├── database.py                # Database operations
│   └── models.py                  # SQLAlchemy models (optional)
│
├── distributors/
│   ├── __init__.py
│   ├── telegram_bot.py            # Telegram bot & digest
│   └── digest_formatter.py        # Format digest messages
│
├── dashboard/
│   └── streamlit_app.py           # Streamlit web dashboard
│
├── config/
│   ├── __init__.py
│   ├── settings.py                # Configuration constants
│   ├── keywords.json              # Keyword database
│   └── rss_feeds.json             # RSS feed URLs
│
├── utils/
│   ├── __init__.py
│   ├── logger.py                  # Logging setup
│   └── helpers.py                 # Utility functions
│
├── scripts/
│   ├── setup_database.py          # Initialize database schema
│   ├── backup.sh                  # Backup script
│   └── cleanup.py                 # Old data cleanup
│
├── data/                          # Created at runtime
│   ├── taraji_ai.db
│   ├── raw/
│   └── exports/
│
├── logs/                          # Created at runtime
│   └── .gitkeep
│
├── tests/
│   ├── test_collectors.py
│   ├── test_processors.py
│   └── test_distributors.py
│
├── main.py                        # Main orchestrator CLI
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── .gitignore
├── README.md
├── PLAN.md                        # This file
└── LICENSE
```

---

## Implementation Roadmap

### Phase 1: Foundation & MVP (Days 1-4)

**Goal:** Basic news collection and storage working locally

**Day 1: Project Setup**
- [ ] Create Oracle Cloud account
- [ ] Provision VM instance (4 cores, 24GB RAM)
- [ ] SSH into VM and configure
- [ ] Install Python, git, dependencies
- [ ] Create project directory structure
- [ ] Initialize git repository
- [ ] Set up virtual environment

**Day 2: Database & Core Infrastructure**
- [ ] Create SQLite database schema
- [ ] Implement database operations (insert, query, update)
- [ ] Set up logging system (loguru)
- [ ] Create configuration management (.env file)
- [ ] Write utility functions
- [ ] Test database operations

**Day 3: First Collector (Google News)**
- [ ] Implement Google News collector
- [ ] Implement keyword filtering
- [ ] Implement language detection
- [ ] Test: collect 20-30 articles
- [ ] Save to database
- [ ] Verify data quality

**Day 4: Testing & Refinement**
- [ ] Run collector multiple times
- [ ] Analyze false positives
- [ ] Refine keyword list
- [ ] Add error handling
- [ ] Test edge cases
- [ ] Document findings

**Deliverable:** Working collector saving 10-30 relevant articles per run

---

### Phase 2: Complete Collection Pipeline (Days 5-8)

**Day 5: Twitter Collector**
- [ ] Implement Twitter collector (snscrape)
- [ ] Configure Twitter-specific keywords
- [ ] Handle rate limiting
- [ ] Test with various queries
- [ ] Integrate with database
- [ ] Compare quality vs Google News

**Day 6: RSS Feeds**
- [ ] Curate list of 15-20 RSS feeds
- [ ] Implement RSS collector
- [ ] Handle parsing errors
- [ ] Filter by keywords
- [ ] Test all feeds
- [ ] Add to database

**Day 7: Content Extraction**
- [ ] Implement article text extraction (newspaper3k)
- [ ] Handle extraction failures gracefully
- [ ] Extract metadata (author, image, date)
- [ ] Test on various news sites
- [ ] Fallback to summary if extraction fails

**Day 8: Processing Pipeline Integration**
- [ ] Implement deduplication logic
- [ ] Implement classification (rule-based)
- [ ] Integrate all processors
- [ ] Create end-to-end pipeline
- [ ] Test with 100+ articles
- [ ] Measure accuracy

**Deliverable:** Complete collection from 3 sources with basic processing

---

### Phase 3: AI Summarization & Automation (Days 9-11)

**Day 9: AI Summarization**
- [ ] Create Google Cloud account (for Gemini API)
- [ ] Get Gemini API key
- [ ] Implement summarizer
- [ ] Test on 20 articles (various languages)
- [ ] Implement fallback (extractive summarization)
- [ ] Add rate limiting

**Day 10: Cron Automation**
- [ ] Create main orchestrator script (`main.py`)
- [ ] Set up cron jobs (every 30 minutes)
- [ ] Test automated runs
- [ ] Monitor logs
- [ ] Fix any issues
- [ ] Verify database growth

**Day 11: Error Handling & Logging**
- [ ] Comprehensive error handling
- [ ] Detailed logging for debugging
- [ ] Email/Telegram alerts on critical errors
- [ ] Automatic retry logic
- [ ] Log rotation
- [ ] Performance monitoring

**Deliverable:** Fully automated collection running every 30 minutes

---

### Phase 4: Distribution (Days 12-14)

**Day 12: Telegram Bot Setup**
- [ ] Create Telegram bot via BotFather
- [ ] Get bot token
- [ ] Create Telegram channel
- [ ] Implement basic bot commands (`/latest`, `/today`)
- [ ] Test sending messages
- [ ] Format messages beautifully

**Day 13: Daily Digest**
- [ ] Implement digest generator
- [ ] Group articles by category
- [ ] Format with emojis and markdown
- [ ] Schedule daily digest (8 AM)
- [ ] Test formatting on mobile
- [ ] Refine layout

**Day 14: Testing & Launch**
- [ ] Full end-to-end test (24 hours)
- [ ] Monitor all components
- [ ] Fix any bugs
- [ ] Optimize performance
- [ ] Official launch
- [ ] Announce Telegram channel

**Deliverable:** Daily Telegram digest published automatically

---

### Phase 5: Dashboard & Polish (Days 15-18)

**Day 15: Streamlit Dashboard**
- [ ] Create basic Streamlit app
- [ ] Implement article browsing
- [ ] Add filters (date, category, language)
- [ ] Add search functionality
- [ ] Deploy on VM (port 8501)
- [ ] Test responsiveness

**Day 16: Dashboard Features**
- [ ] Statistics page (charts, metrics)
- [ ] Duplicate grouping view
- [ ] Manual moderation interface
- [ ] Export functionality (CSV, JSON)
- [ ] Improve UI/UX

**Day 17: Monitoring & Alerts**
- [ ] Collection health checks
- [ ] Daily statistics email/Telegram
- [ ] Alert on zero articles collected
- [ ] Alert on high error rate
- [ ] Database size monitoring
- [ ] API quota monitoring (Gemini)

**Day 18: Documentation & Backup**
- [ ] Write comprehensive README
- [ ] Document setup process
- [ ] Create troubleshooting guide
- [ ] Set up automated backups
- [ ] Test backup restoration
- [ ] Create maintenance checklist

**Deliverable:** Complete system with web dashboard and monitoring

---

### Phase 6: Optimization & Expansion (Days 19-21)

**Day 19: Quality Improvements**
- [ ] Analyze false positives (manual review of 100 articles)
- [ ] Refine keyword matching
- [ ] Improve deduplication accuracy
- [ ] Better classification (consider ML if enough data)
- [ ] Multilingual improvements (Arabic handling)

**Day 20: Performance Optimization**
- [ ] Profile code for bottlenecks
- [ ] Optimize database queries
- [ ] Add database indexes if needed
- [ ] Reduce API calls where possible
- [ ] Optimize cron job runtime (target <5 min)

**Day 21: Future-Proofing**
- [ ] Modularize code for easy expansion
- [ ] Add more RSS feeds
- [ ] Research additional sources
- [ ] Plan ML classifier (if data sufficient)
- [ ] Document expansion paths

**Deliverable:** Optimized, production-ready system

---

## Deployment Guide

### Initial Deployment

**1. Clone/Upload Code to VM**

```bash
# If you have git repo
git clone https://github.com/yourusername/taraji_ai.git
cd taraji_ai

# Or manually upload files via SCP
scp -r -i ~/taraji-ai-vm.key ./taraji_ai ubuntu@<PUBLIC_IP>:~/
```

**2. Set Up Python Environment**

```bash
cd ~/taraji_ai

# Create virtual environment
python3.11 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

**3. Configure Environment Variables**

```bash
# Copy template
cp .env.example .env

# Edit with your API keys
nano .env
```

**.env file:**
```bash
# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHANNEL_ID=@taraji_news

# Google Gemini API
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Database
DATABASE_PATH=data/taraji_ai.db

# Logging
LOG_LEVEL=INFO
```

**4. Initialize Database**

```bash
# Run database setup script
python scripts/setup_database.py
```

**5. Test Manually**

```bash
# Test collection
python main.py collect --test

# Test processing
python main.py process

# Test Telegram (send test message)
python main.py test-telegram
```

**6. Set Up Cron Jobs**

```bash
# Edit crontab
crontab -e
```

**Add these lines:**
```bash
# Taraji AI News Collection - every 30 minutes
*/30 * * * * cd /home/ubuntu/taraji_ai && /home/ubuntu/taraji_ai/venv/bin/python main.py collect >> logs/cron.log 2>&1

# Daily digest - every day at 8:00 AM UTC
0 8 * * * cd /home/ubuntu/taraji_ai && /home/ubuntu/taraji_ai/venv/bin/python main.py send-digest --daily >> logs/cron.log 2>&1

# Weekly cleanup - every Sunday at midnight
0 0 * * 0 cd /home/ubuntu/taraji_ai && /home/ubuntu/taraji_ai/venv/bin/python scripts/cleanup.py >> logs/cron.log 2>&1

# Weekly backup - every Sunday at 1:00 AM
0 1 * * 0 cd /home/ubuntu/taraji_ai && bash scripts/backup.sh >> logs/cron.log 2>&1
```

**7. Monitor First Runs**

```bash
# Watch logs in real-time
tail -f logs/app.log

# Check cron logs
tail -f logs/cron.log

# Check database growth
sqlite3 data/taraji_ai.db "SELECT COUNT(*) FROM articles;"
```

### Updating the System

```bash
# SSH into VM
ssh -i ~/taraji-ai-vm.key ubuntu@<PUBLIC_IP>

# Navigate to project
cd ~/taraji_ai

# Activate venv
source venv/bin/activate

# Pull latest code (if using git)
git pull

# Update dependencies if requirements changed
pip install -r requirements.txt

# Restart (cron will pick up changes automatically)
# Or manually test
python main.py collect --test
```

---

## Monitoring & Maintenance

### Daily Checks (Automated)

**Health check script:**
```python
# scripts/health_check.py
def daily_health_check():
    # Check articles collected in last 24h
    count = get_articles_count_24h()

    if count == 0:
        send_alert("⚠️ ALERT: No articles collected in last 24 hours!")
    elif count < 5:
        send_alert("⚠️ WARNING: Only {} articles collected today (expected 20-50)".format(count))

    # Check database size
    db_size_mb = get_database_size_mb()
    if db_size_mb > 500:
        send_alert("⚠️ WARNING: Database size is {} MB".format(db_size_mb))

    # Check API quotas
    gemini_usage = get_gemini_usage_today()
    if gemini_usage > 1400:  # 1500 limit
        send_alert("⚠️ WARNING: Gemini API usage at {}/1500 today".format(gemini_usage))

    # Send daily summary
    send_telegram_message(f"""
📊 Taraji AI Daily Report

Articles collected: {count}
Database size: {db_size_mb} MB
Gemini API calls: {gemini_usage}/1500
System status: ✅ Healthy
""")
```

### Weekly Maintenance

**Every Sunday:**
1. Review collection statistics
2. Check for broken sources (RSS feeds, scrapers)
3. Review false positives (sample 20 articles)
4. Update keyword list if needed
5. Check disk space
6. Verify backups

**Script:**
```bash
# scripts/weekly_maintenance.sh
#!/bin/bash

echo "=== Taraji AI Weekly Maintenance ==="
echo "Date: $(date)"

# Database statistics
echo -e "\n--- Database Stats ---"
sqlite3 data/taraji_ai.db "
SELECT
    COUNT(*) as total_articles,
    COUNT(DISTINCT source) as unique_sources,
    COUNT(CASE WHEN collected_date >= date('now', '-7 days') THEN 1 END) as last_week
FROM articles;
"

# Disk usage
echo -e "\n--- Disk Usage ---"
du -sh data/
du -sh logs/

# Log errors from last week
echo -e "\n--- Recent Errors ---"
grep ERROR logs/app.log | tail -20

# Backup status
echo -e "\n--- Backups ---"
ls -lh data/exports/ | tail -5
```

### Monthly Reviews

1. Analyze article categories distribution
2. Review deduplication accuracy
3. Consider adding new sources
4. Evaluate summarization quality
5. Update documentation
6. Plan new features

---

## Risks & Mitigation

### 1. Source Availability Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Twitter blocks snscrape | High | Medium | Use Nitter as fallback; add more RSS feeds |
| RSS feeds go offline | Medium | Low | Monitor feeds weekly; have 20+ feeds for redundancy |
| Google News changes | Medium | Low | Use multiple collectors; monitor for errors |

### 2. API & Service Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Gemini API quota exceeded | Medium | Low | Implement rate limiting; fallback to extractive summarization |
| Telegram API down | Low | Very Low | Queue messages; retry later |
| Oracle Cloud discontinues free tier | High | Very Low | Monitor Oracle announcements; have migration plan |

### 3. Data Quality Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Too many false positives | Medium | Medium | Refine keywords; add negative keywords; manual review |
| Missing important news | High | Low | Multiple sources; broad keyword coverage |
| Duplicate detection fails | Low | Medium | Manual deduplication in dashboard; tune thresholds |

### 4. Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Database corruption | High | Very Low | Daily backups; WAL mode for SQLite |
| Disk space full | Medium | Low | Weekly cleanup; monitor disk usage |
| VM crashes | Medium | Very Low | Cron automatically restarts; systemd service (optional) |
| Code bugs | Medium | Medium | Comprehensive error handling; logging; testing |

### 5. Legal & Ethical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Scraping violates ToS | Low | Medium | Use official APIs when possible; respect robots.txt; personal use |
| Copyright issues | Low | Low | Link to original sources; don't copy full articles; summaries are transformative |

---

## Future Enhancements

### Short-term (Month 2-3)

**Content Improvements:**
- [ ] Add Facebook monitoring (via RSS Bridge or Graph API)
- [ ] Add YouTube monitoring (channel videos, mentions)
- [ ] Add sports forums (Reddit, fan forums)
- [ ] Image extraction and storage
- [ ] Video clip detection

**Feature Improvements:**
- [ ] Sentiment analysis (positive/negative news)
- [ ] Trending topics detection
- [ ] Player name extraction (NER)
- [ ] Match result parsing (structured data)
- [ ] Historical comparison (e.g., "best start to season since 2019")

**Distribution Enhancements:**
- [ ] WhatsApp integration (Business API or unofficial)
- [ ] Facebook auto-posting
- [ ] Twitter auto-posting
- [ ] Email newsletter
- [ ] Mobile app (PWA or React Native)

### Medium-term (Month 4-6)

**AI/ML Upgrades:**
- [ ] Train custom classification model
- [ ] Fine-tune LLM on football domain
- [ ] Automated importance scoring
- [ ] Predict trending stories before they blow up
- [ ] Generate custom headlines for social media

**Technical Improvements:**
- [ ] Migrate to PostgreSQL (if needed)
- [ ] Add vector database for semantic search (Weaviate/Qdrant)
- [ ] Real-time monitoring (WebSockets)
- [ ] GraphQL API for dashboard
- [ ] Containerize with Docker
- [ ] CI/CD pipeline

**Analytics:**
- [ ] Advanced statistics dashboard
- [ ] Source reliability tracking
- [ ] Keyword trending over time
- [ ] Engagement metrics (if posting to social media)
- [ ] Performance analytics (collector speed, accuracy)

### Long-term (Month 7+)

**Advanced Features:**
- [ ] Multi-club monitoring (add other teams for comparison)
- [ ] Live match commentary aggregation
- [ ] Automatic fact-checking
- [ ] Interview transcription (YouTube videos)
- [ ] Multi-language article translation
- [ ] Custom alerts (e.g., "notify me only for transfers")

**Monetization (optional):**
- [ ] Premium tier with instant notifications
- [ ] API access for other developers
- [ ] White-label solution for other clubs
- [ ] Sponsored content identification

**Community Features:**
- [ ] User submissions
- [ ] Voting on article quality
- [ ] Comments/discussions
- [ ] Fan sentiment tracking

---

## Cost Summary

| Service | Usage | Free Tier | Expected Cost |
|---------|-------|-----------|---------------|
| Oracle Cloud VM | 24/7 hosting | 4 ARM cores, 24GB RAM, 200GB disk | **$0/month** |
| Google Gemini API | ~50 summaries/day | 1,500/day | **$0/month** |
| Telegram Bot | Unlimited messages | Unlimited | **$0/month** |
| Domain (optional) | Website URL | N/A | $10-15/year |
| **Total** | | | **$0-1.25/month** |

---

## Success Metrics

**Week 1:**
- [ ] Collect 50+ articles/day
- [ ] <10% false positives
- [ ] 0 crashes

**Month 1:**
- [ ] 1,500+ articles collected
- [ ] 99% uptime
- [ ] Daily Telegram digest sent reliably
- [ ] <5% false positives

**Month 3:**
- [ ] 5,000+ articles collected
- [ ] Multiple sources working
- [ ] Dashboard with 100+ daily active users
- [ ] 95%+ deduplication accuracy

**Month 6:**
- [ ] 10,000+ articles
- [ ] Auto-posting to social media
- [ ] ML classifier trained
- [ ] Featured on club fan sites

---

## Support & Resources

**Documentation:**
- Oracle Cloud: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm
- Google Gemini: https://ai.google.dev/tutorials/python_quickstart
- Telegram Bots: https://core.telegram.org/bots/api
- Python libraries: See requirements.txt

**Community:**
- Oracle Cloud forums
- Python Discord servers
- r/datascience, r/webscraping
- Football data community

**Contact:**
- GitHub Issues: [your repo URL]
- Telegram: [your username]
- Email: [your email]

---

## Conclusion

This plan provides a complete roadmap for building Taraji AI - a fully automated, zero-cost news monitoring system. The Oracle Cloud Free Tier gives us enterprise-grade infrastructure without any recurring costs, and the modular architecture allows for easy expansion.

**Next Steps:**
1. Set up Oracle Cloud account and VM
2. Create project structure
3. Start with Phase 1 (Days 1-4)
4. Iterate based on real data

Let's build something great for the Taraji community! 🔴🟡

---

**Version:** 1.0
**Last Updated:** 2025-11-19
**Author:** Taraji AI Team
