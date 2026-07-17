# Taraji AI

Automated news monitoring system for Espérance Sportive de Tunis.

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python main.py init
```

### 3. Run First Collection (Test Mode)

```bash
python main.py collect --test
```

This will:
- Collect news from Google News
- Filter by club keywords
- Detect languages
- Store in database
- Show sample results

### 4. View Statistics

```bash
python main.py stats
```

## Project Structure

```
taraji_AI/
├── collectors/        # Data collection (Google News, RSS)
├── processors/        # Keyword filter, extraction, language detection, AI
├── storage/           # Database operations
├── distributors/      # Telegram bot
├── config/            # Configuration (settings.py, keywords.json)
├── utils/             # Utilities and logging
├── scripts/           # Dev utilities (inspect/view articles, keyword checks)
├── data/              # Data storage (database, raw files)
├── logs/              # Application logs
└── main.py            # Main entry point
```

## Configuration

### Keywords
Edit `config/keywords.json` to add/modify club keywords:
- `exact`: Unambiguous club names — always match, immune to negative keywords
- `exact_ambiguous`: Short names shared with lookalikes (bare "الترجي") — negative keywords can veto these
- `contextual`: Requires context words (like "EST" + "Tunis")
- `negative`: Exclusions (other clubs, Taraji P. Henson, etc.)

Test changes with `python scripts/check_keywords.py "some headline"`.

### Monitored players
Edit `config/players.json` to follow individual players beyond club-name coverage (see GUIDE.md for field details):
- `squad`: current EST players on departure watch
- `targets`: reported transfer targets (their news never mentions EST until a deal is close)

### Settings
Edit `config/settings.py` for:
- RSS feed sources (`RSS_FEEDS`)
- Google News query options
- Database paths
- Log levels

## Commands

```bash
# Initialize database
python main.py init

# Collect news (collect + extract + AI process + store)
python main.py collect

# Collect in test mode (shows samples)
python main.py collect --test

# Send unpublished articles to Telegram
python main.py distribute

# Verify bot token and discover chat ids
python main.py telegram-setup

# Show statistics
python main.py stats
```

## Deployment

The pipeline runs on GitHub Actions every 15 minutes
(`.github/workflows/collect.yml`). State persists by committing
`data/taraji_ai.db` back to the repository after each run that finds
new articles. Secrets (`GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID`) live in the repository's Actions secrets.

## Status

✅ Google News + RSS collectors
✅ Keyword filtering (contextual matching + negative keywords)
✅ Content extraction (Google News URL decoding + trafilatura)
✅ Batched AI processing: relevance check, classification, FR+AR
   summaries and duplicate detection in one Gemini call per run
✅ Scheduled collection via GitHub Actions (15-min cadence via cron-job.org)
✅ Telegram distributor (live, posting to test chat; photo posts + bilingual)
✅ Workflow failure alerts via Telegram
⏳ Switch to public channel @taraji_news (pending output validation)

Everything else planned: see `ROADMAP.md`.

## License

MIT
