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

# Collect news
python main.py collect

# Collect in test mode (shows samples)
python main.py collect --test

# Show statistics
python main.py stats
```

## Next Steps

See **PLAN.md** for the complete implementation roadmap.

**Phase 1 (Current):** MVP - Basic collection and storage
**Phase 2:** Add Twitter and RSS collectors
**Phase 3:** AI summarization
**Phase 4:** Telegram distribution
**Phase 5:** Web dashboard

## Status

✅ Project structure
✅ Database schema
✅ Google News collector
✅ Keyword filtering (with contextual matching)
✅ Language detection
⏳ Twitter collector (Phase 2)
⏳ RSS feeds (Phase 2)
⏳ AI summarization (Phase 3)
⏳ Telegram bot (Phase 4)
⏳ Web dashboard (Phase 5)

## License

MIT
