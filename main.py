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
from collectors import collect_google_news, collect_rss
from processors import create_keyword_filter, detect_language, create_classifier, create_summarizer, create_content_extractor


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

    # Step 1: Collect from all sources
    log.info("\n[1/8] Collecting from Google News...")
    google_articles = collect_google_news()
    log.info(f"Collected {len(google_articles)} articles from Google News")

    log.info("\n[2/8] Collecting from RSS feeds...")
    rss_articles = collect_rss()
    log.info(f"Collected {len(rss_articles)} articles from RSS feeds")

    # Combine all articles and deduplicate by URL
    all_articles = google_articles + rss_articles
    seen_urls = set()
    articles = []
    for article in all_articles:
        url = article.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            articles.append(article)

    duplicates_removed = len(all_articles) - len(articles)
    log.info(f"Total: {len(articles)} unique articles ({duplicates_removed} duplicates removed)")

    if not articles:
        log.warning("No articles collected!")
        return

    # Step 3: Filter by keywords
    log.info("\n[3/8] Filtering by keywords...")
    keyword_filter = create_keyword_filter()
    filtered_articles = keyword_filter.filter_articles(articles)

    if not filtered_articles:
        log.warning("No relevant articles after filtering!")
        return

    log.info(f"Found {len(filtered_articles)} relevant articles")

    # Step 4: Extract full article content from URLs
    log.info("\n[4/8] Extracting article content...")
    extractor = create_content_extractor()
    extracted_count = 0
    for article in filtered_articles:
        url = article.get('url', '')
        if url:
            result = extractor.extract(url)
            if result and result.get('text'):
                article['content'] = result['text']
                article['author'] = ', '.join(result.get('authors', []))
                article['image_url'] = result.get('top_image', '')
                extracted_count += 1

    log.info(f"Extracted content from {extracted_count}/{len(filtered_articles)} articles")

    # Step 5: Detect languages
    log.info("\n[5/8] Detecting languages...")
    for article in filtered_articles:
        # Use extracted content or fallback to description
        text = article.get('content', '') or f"{article.get('title', '')} {article.get('description', '')}"
        article['language'] = detect_language(text)

    # Step 6: Classify articles
    log.info("\n[6/8] Classifying articles...")
    classifier = create_classifier()
    for article in filtered_articles:
        title = article.get('title', '')
        content = article.get('content', '') or article.get('description', '') or ''
        article['category'] = classifier.classify(title, content)

    # Step 7: Summarize articles
    log.info("\n[7/8] Summarizing articles...")
    summarizer = create_summarizer()
    summarized_count = 0
    for article in filtered_articles:
        title = article.get('title', '')
        # Use extracted content for summarization, fallback to description
        content = article.get('content', '') or article.get('description', '') or ''
        language = article.get('language', 'fr')

        # Generate summary
        summary = summarizer.summarize(title, content, language, max_sentences=2)
        if summary:
            article['summary'] = summary
            summarized_count += 1

    log.info(f"Summarized {summarized_count}/{len(filtered_articles)} articles")

    # Show summarizer stats
    stats = summarizer.get_stats()
    log.info(f"  Gemini API: {stats['requests_today']}/{stats['daily_limit']} requests used today")

    # Step 8: Store in database
    log.info("\n[8/8] Storing in database...")
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


def cmd_classify():
    """Classify existing articles in database"""
    log.info("=" * 60)
    log.info("Classifying Existing Articles")
    log.info("=" * 60)

    classifier = create_classifier()

    with get_db() as db:
        # Get all articles
        cursor = db.conn.cursor()
        cursor.execute("SELECT id, title, content, summary FROM articles")
        articles = cursor.fetchall()

        if not articles:
            log.warning("No articles found in database!")
            return

        log.info(f"\nFound {len(articles)} articles to classify...")

        classified_count = 0
        category_counts = {}

        for article in articles:
            article_id = article['id']
            title = article['title']
            content = article['content'] or article['summary'] or ''

            # Classify
            category = classifier.classify(title, content)

            # Update database
            cursor.execute("""
                UPDATE articles
                SET category = ?
                WHERE id = ?
            """, (category, article_id))

            classified_count += 1
            category_counts[category] = category_counts.get(category, 0) + 1

        db.conn.commit()

        log.info(f"\n✅ Classified {classified_count} articles")
        log.info("\nCategory distribution:")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            cat_info = classifier.get_category_info(category)
            emoji = cat_info['emoji']
            log.info(f"  {emoji} {category}: {count}")

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

    # Classify command
    subparsers.add_parser('classify', help='Classify existing articles in database')

    args = parser.parse_args()

    # Execute command
    if args.command == 'init':
        cmd_init()
    elif args.command == 'collect':
        cmd_collect(test_mode=args.test)
    elif args.command == 'stats':
        cmd_stats()
    elif args.command == 'classify':
        cmd_classify()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
