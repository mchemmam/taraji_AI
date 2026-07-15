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
├── collectors/        # Data collection modules
├── processors/        # Processing (filtering, language detection)
├── storage/          # Database operations
├── config/           # Configuration files
├── utils/            # Utilities and logging
├── data/             # Data storage (database, raw files)
├── logs/             # Application logs
└── main.py           # Main entry point
```

## Configuration

### Keywords
Edit `config/keywords.json` to add/modify club keywords:
- `exact`: Direct matches (with language variants)
- `contextual`: Requires context words (like "EST" + "Tunis")
- `negative`: Exclusions (other clubs, Taraji P. Henson, etc.)

### Settings
Edit `config/settings.py` for:
- Collection intervals
- API limits
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
✅ Batched AI processing: relevance check, classification and
   FR/AR summaries in one Gemini call per run (`gemini-2.5-flash`)
✅ Scheduled collection via GitHub Actions
✅ Telegram distributor (pending bot token configuration)
⏳ Daily digest
⏳ Web dashboard (static site on GitHub Pages)
❌ Twitter/X (dropped - no viable free access in 2026)

## License

MIT
