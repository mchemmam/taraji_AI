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
from storage import init_database, get_db
from collectors import collect_google_news
from processors import create_keyword_filter, detect_language


def cmd_init():
    """Initialize the database"""
    log.info("Initializing database...")
    init_database()
    log.info("Database initialization complete!")


def cmd_collect(test_mode=False):
    """Run news collection"""
    log.info("=" * 60)
    log.info("Starting Taraji AI News Collection")
    log.info("=" * 60)

    # Step 1: Collect from Google News
    log.info("\n[1/4] Collecting from Google News...")
    articles = collect_google_news()

    if not articles:
        log.warning("No articles collected!")
        return

    log.info(f"Collected {len(articles)} articles")

    # Step 2: Filter by keywords
    log.info("\n[2/4] Filtering by keywords...")
    keyword_filter = create_keyword_filter()
    filtered_articles = keyword_filter.filter_articles(articles)

    if not filtered_articles:
        log.warning("No relevant articles after filtering!")
        return

    log.info(f"Found {len(filtered_articles)} relevant articles")

    # Step 3: Detect languages
    log.info("\n[3/4] Detecting languages...")
    for article in filtered_articles:
        text = f"{article.get('title', '')} {article.get('description', '')}"
        article['language'] = detect_language(text)

    # Step 4: Store in database
    log.info("\n[4/4] Storing in database...")
    stored_count = 0
    duplicate_count = 0

    with get_db() as db:
        for article in filtered_articles:
            article_id = db.insert_article(article)
            if article_id:
                stored_count += 1
            else:
                duplicate_count += 1

    log.info(f"Stored {stored_count} new articles, {duplicate_count} duplicates")

    # Print summary
    log.info("\n" + "=" * 60)
    log.info("Collection Summary:")
    log.info(f"  Total collected: {len(articles)}")
    log.info(f"  Relevant: {len(filtered_articles)}")
    log.info(f"  New articles stored: {stored_count}")
    log.info(f"  Duplicates skipped: {duplicate_count}")
    log.info("=" * 60)

    if test_mode:
        # Show some sample articles
        log.info("\nSample articles:")
        for i, article in enumerate(filtered_articles[:5], 1):
            log.info(f"\n  {i}. {article['title']}")
            log.info(f"     Source: {article['source']}")
            log.info(f"     Language: {article.get('language', 'unknown')}")
            log.info(f"     Matched: {article.get('matched_keyword', 'N/A')}")


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

    # Init command
    subparsers.add_parser('init', help='Initialize the database')

    # Collect command
    collect_parser = subparsers.add_parser('collect', help='Collect news articles')
    collect_parser.add_argument('--test', action='store_true', help='Test mode - show sample results')

    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')

    args = parser.parse_args()

    # Execute command
    if args.command == 'init':
        cmd_init()
    elif args.command == 'collect':
        cmd_collect(test_mode=args.test)
    elif args.command == 'stats':
        cmd_stats()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
