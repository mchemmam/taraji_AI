#!/usr/bin/env python3
"""
Taraji AI - Main orchestrator script
"""
import sys
import argparse
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from utils import log
from config import settings
from storage import init_database, get_db
from collectors import collect_google_news, collect_rss
from processors import (
    create_keyword_filter,
    detect_language,
    create_ai_processor,
    create_content_extractor,
)
from distributors import create_telegram_distributor


def cmd_init():
    """Initialize the database"""
    log.info("Initializing database...")
    init_database()
    log.info("Database initialization complete!")


def _dedupe_by_url(articles, key='url'):
    seen = set()
    unique = []
    for article in articles:
        value = article.get(key) or article.get('url', '')
        if value and value not in seen:
            seen.add(value)
            unique.append(article)
    return unique


def cmd_collect(test_mode=False):
    """Run news collection"""
    log.info("=" * 60)
    log.info("Starting Taraji AI News Collection")
    log.info("=" * 60)

    # Step 1: Collect from all sources
    log.info("\n[1/7] Collecting from Google News...")
    google_articles = collect_google_news()
    log.info(f"Collected {len(google_articles)} articles from Google News")

    log.info("\n[2/7] Collecting from RSS feeds...")
    rss_articles = collect_rss()
    log.info(f"Collected {len(rss_articles)} articles from RSS feeds")

    articles = _dedupe_by_url(google_articles + rss_articles)
    log.info(f"Total: {len(articles)} unique articles")

    if not articles:
        log.warning("No articles collected!")
        return

    # Step 3: Filter by keywords (cheap prefilter before any network/AI work)
    log.info("\n[3/7] Filtering by keywords...")
    keyword_filter = create_keyword_filter()
    filtered_articles = keyword_filter.filter_articles(articles)

    if not filtered_articles:
        log.warning("No relevant articles after filtering!")
        return

    # Step 4: Drop articles we already have - avoids re-extracting and
    # re-summarizing the same stories on every scheduled run
    log.info("\n[4/7] Checking for new articles...")
    with get_db() as db:
        known_urls = db.get_existing_urls([a['url'] for a in filtered_articles])
    new_articles = [a for a in filtered_articles if a['url'] not in known_urls]
    log.info(f"{len(new_articles)} new articles ({len(filtered_articles) - len(new_articles)} already known)")

    if not new_articles:
        log.info("Nothing new this run.")
        return

    # Step 5: Resolve URLs and extract full article content
    log.info("\n[5/7] Extracting article content...")
    extractor = create_content_extractor()
    extracted_count = 0
    for article in new_articles:
        url = article.get('url', '')
        if not url:
            continue
        result = extractor.extract(url)
        if result:
            article['content'] = result['text']
            article['author'] = ', '.join(result.get('authors', []))
            article['image_url'] = result.get('top_image') or ''
            article['resolved_url'] = result.get('resolved_url', url)
            extracted_count += 1
        else:
            article['resolved_url'] = extractor.resolve_url(url)
    log.info(f"Extracted content from {extracted_count}/{len(new_articles)} articles")

    # Same story can arrive via different collected URLs (Google News + RSS);
    # after resolution we can catch those duplicates
    new_articles = _dedupe_by_url(new_articles, key='resolved_url')
    with get_db() as db:
        known_resolved = db.get_existing_urls(
            [a.get('resolved_url', '') for a in new_articles if a.get('resolved_url')]
        )
    new_articles = [a for a in new_articles if a.get('resolved_url', a['url']) not in known_resolved]

    if not new_articles:
        log.info("All articles were duplicates after URL resolution.")
        return

    # Step 6: Detect languages
    log.info("\n[6/7] Detecting languages...")
    for article in new_articles:
        text = article.get('content', '') or f"{article.get('title', '')} {article.get('description', '')}"
        article['language'] = detect_language(text)

    # Step 7: AI processing - one batched Gemini call for relevance check,
    # classification and summaries (rule-based fallback inside)
    log.info("\n[7/7] AI processing (relevance + category + summary)...")
    ai = create_ai_processor()
    new_articles, rejected = ai.process_articles(new_articles)
    stats = ai.get_stats()
    log.info(f"  Gemini requests this run: {stats['requests_made']} (available: {stats['gemini_available']})")

    # Remember rejected URLs so they are not re-extracted and re-judged
    # on every subsequent 15-minute run
    if rejected:
        with get_db() as db:
            for article, reason in rejected:
                db.insert_rejected_url(
                    article['url'], article.get('resolved_url'), reason
                )

    # Store in database
    log.info("\nStoring in database...")
    stored_count = 0
    duplicate_count = 0
    with get_db() as db:
        for article in new_articles:
            article_id = db.insert_article(article)
            if article_id:
                stored_count += 1
            else:
                duplicate_count += 1

        # Prune bulky old data while this run is committing a DB change
        # anyway - article text is only needed until its summary exists
        if stored_count:
            pruned, dropped = db.prune_old_data(settings.CONTENT_RETENTION_DAYS)
            if pruned or dropped:
                log.info(f"Pruned content from {pruned} old articles, "
                         f"dropped {dropped} old rejected URLs")

    log.info("\n" + "=" * 60)
    log.info("Collection Summary:")
    log.info(f"  Total collected: {len(articles)}")
    log.info(f"  New & relevant: {len(new_articles)}")
    log.info(f"  Stored: {stored_count} (duplicates skipped: {duplicate_count})")
    log.info("=" * 60)

    if test_mode:
        log.info("\nSample articles:")
        for i, article in enumerate(new_articles[:5], 1):
            log.info(f"\n  {i}. {article['title']}")
            log.info(f"     Source: {article['source']} | Lang: {article.get('language')} | Cat: {article.get('category')}")
            log.info(f"     Summary: {(article.get('summary') or '')[:150]}")


def cmd_distribute():
    """Send unpublished articles to Telegram"""
    log.info("=" * 60)
    log.info("Distributing new articles to Telegram")
    log.info("=" * 60)

    distributor = create_telegram_distributor()
    if not distributor.enabled:
        log.error("Telegram not configured (need TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")
        return

    with get_db() as db:
        stats = distributor.distribute(db)

    log.info(f"Done: {stats['sent']} sent, {stats['failed']} failed")


def cmd_telegram_setup():
    """Verify bot token and show recent chat IDs (to find your test chat ID)"""
    import os
    import requests as rq

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        log.error("TELEGRAM_BOT_TOKEN not set")
        return

    me = rq.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15).json()
    if not me.get('ok'):
        log.error(f"Bot token invalid: {me.get('description')}")
        return

    bot = me['result']
    log.info(f"✅ Bot OK: @{bot['username']} ({bot.get('first_name')})")

    updates = rq.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=15).json()
    chats = {}
    for update in updates.get('result', []):
        msg = update.get('message') or update.get('channel_post') or {}
        chat = msg.get('chat')
        if chat:
            chats[chat['id']] = chat

    if chats:
        log.info("Recent chats seen by the bot (use one as TELEGRAM_CHAT_ID):")
        for chat_id, chat in chats.items():
            name = chat.get('title') or chat.get('username') or chat.get('first_name')
            log.info(f"  chat_id={chat_id}  type={chat['type']}  name={name}")
    else:
        log.info(f"No recent messages. Send any message to @{bot['username']} on Telegram, then rerun this command.")


def cmd_stats():
    """Show database statistics"""
    log.info("Database Statistics:")
    log.info("=" * 60)

    with get_db() as db:
        stats = db.get_stats_summary()

        log.info(f"\nTotal articles: {stats['total_articles']}")
        log.info(f"Last 24 hours: {stats['last_24h']}")
        log.info(f"Last 7 days: {stats['last_7days']}")

        if stats['by_category']:
            log.info("\nBy category (last 7 days):")
            for category, count in stats['by_category'].items():
                log.info(f"  {category}: {count}")

        if stats['by_language']:
            log.info("\nBy language (last 7 days):")
            for lang, count in stats['by_language'].items():
                log.info(f"  {lang}: {count}")

    log.info("=" * 60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Taraji AI - News Monitoring System")

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    subparsers.add_parser('init', help='Initialize the database')

    collect_parser = subparsers.add_parser('collect', help='Collect news articles')
    collect_parser.add_argument('--test', action='store_true', help='Test mode - show sample results')

    subparsers.add_parser('distribute', help='Send unpublished articles to Telegram')
    subparsers.add_parser('telegram-setup', help='Verify bot token and list chat IDs')
    subparsers.add_parser('stats', help='Show database statistics')

    args = parser.parse_args()

    if args.command == 'init':
        cmd_init()
    elif args.command == 'collect':
        cmd_collect(test_mode=args.test)
    elif args.command == 'distribute':
        cmd_distribute()
    elif args.command == 'telegram-setup':
        cmd_telegram_setup()
    elif args.command == 'stats':
        cmd_stats()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
