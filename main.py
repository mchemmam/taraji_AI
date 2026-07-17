#!/usr/bin/env python3
"""
Taraji AI - Main orchestrator script
"""
import re
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
from distributors import create_telegram_distributor, create_facebook_distributor


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


# Whole-word patterns for the blocked publishers (see settings.SOURCE_BLOCKLIST).
# Word boundaries keep "msn" from matching a random substring inside a base64
# Google News link while still catching the "MSN" publisher and msn.com.
_BLOCKED_SOURCE_PATTERNS = [
    re.compile(rf'\b{re.escape(name.lower())}\b')
    for name in settings.SOURCE_BLOCKLIST
]


def _is_blocked_source(article):
    """True if the article's publisher or URL matches SOURCE_BLOCKLIST."""
    haystack = ' '.join(filter(None, [
        article.get('source') or '',
        article.get('url') or '',
        article.get('resolved_url') or '',
    ])).lower()
    return any(pattern.search(haystack) for pattern in _BLOCKED_SOURCE_PATTERNS)


def _drop_blocked_sources(articles):
    """Remove blocked-publisher articles, logging how many were dropped."""
    if not _BLOCKED_SOURCE_PATTERNS:
        return articles
    kept = [a for a in articles if not _is_blocked_source(a)]
    dropped = len(articles) - len(kept)
    if dropped:
        log.info(f"Dropped {dropped} article(s) from blocked sources "
                 f"({', '.join(settings.SOURCE_BLOCKLIST)})")
    return kept


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

    # Drop blocked publishers (e.g. MSN) before any network/AI work - they
    # republish stale stories under refreshed dates. Matched on publisher name
    # here; a second pass after URL resolution catches domain-level republishes.
    articles = _drop_blocked_sources(articles)

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

    # Blocked publishers can hide behind a Google News attribution and only
    # reveal themselves (msn.com) once the redirect is resolved - drop those too
    new_articles = _drop_blocked_sources(new_articles)
    if not new_articles:
        log.info("All new articles were from blocked sources.")
        return

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
    # classification, FR/AR summaries and duplicate detection (rule-based
    # fallback inside). Recent titles let the model reject re-reports of
    # stories we already covered via another source or language.
    log.info("\n[7/7] AI processing (relevance + category + summary + dedup)...")
    with get_db() as db:
        recent_titles = [a['title'] for a in db.get_recent_articles(hours=48, limit=40)]
    ai = create_ai_processor()
    new_articles, rejected = ai.process_articles(new_articles, recent_titles=recent_titles)
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
    """Send unpublished articles to every configured channel"""
    log.info("=" * 60)
    log.info("Distributing new articles")
    log.info("=" * 60)

    distributors = [create_telegram_distributor(), create_facebook_distributor()]
    enabled = [d for d in distributors if d.enabled]
    if not enabled:
        log.error("No distribution channel configured "
                  "(need TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID and/or "
                  "FACEBOOK_PAGE_ID/FACEBOOK_PAGE_ACCESS_TOKEN)")
        return

    for distributor in enabled:
        with get_db() as db:
            stats = distributor.distribute(db)
        log.info(f"{distributor.channel}: {stats['sent']} sent, {stats['failed']} failed")


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


def cmd_facebook_setup():
    """Verify the Page token, or walk through generating one (one-time setup)"""
    import os
    import requests as rq

    graph = "https://graph.facebook.com/v23.0"

    page_token = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')
    if page_token:
        data = rq.get(f"{graph}/me",
                      params={'fields': 'id,name', 'access_token': page_token},
                      timeout=15).json()
        if 'error' in data:
            log.error(f"Page token invalid: {data['error'].get('message')}")
            return
        log.info(f"✅ Page token OK: {data['name']} (page id {data['id']})")
        page_id = os.getenv('FACEBOOK_PAGE_ID')
        if page_id and page_id != data['id']:
            log.warning(f"FACEBOOK_PAGE_ID is {page_id} but the token belongs "
                        f"to page {data['id']} - fix FACEBOOK_PAGE_ID")
        elif not page_id:
            log.warning(f"FACEBOOK_PAGE_ID not set - set it to {data['id']}")
        else:
            log.info("Ready to post. Add both values as GitHub Actions secrets.")
        return

    # No page token yet - do the one-time exchange:
    # short-lived user token -> long-lived user token -> permanent page token
    app_id = os.getenv('FACEBOOK_APP_ID')
    app_secret = os.getenv('FACEBOOK_APP_SECRET')
    user_token = os.getenv('FACEBOOK_USER_TOKEN')

    if not (app_id and app_secret and user_token):
        log.info("One-time Facebook setup - do this once:")
        log.info("  1. Create the Facebook Page (Taraji Press) with your personal account")
        log.info("  2. Create an app on https://developers.facebook.com (type: Business/Other)")
        log.info("  3. Open https://developers.facebook.com/tools/explorer - pick your app,")
        log.info("     generate a User Token with permissions: pages_show_list,")
        log.info("     pages_manage_posts, pages_read_engagement")
        log.info("  4. Put in .env: FACEBOOK_APP_ID + FACEBOOK_APP_SECRET (app dashboard")
        log.info("     > Settings > Basic) and FACEBOOK_USER_TOKEN (from step 3)")
        log.info("  5. Rerun this command - it prints the page id and a long-lived Page")
        log.info("     token to save as FACEBOOK_PAGE_ID / FACEBOOK_PAGE_ACCESS_TOKEN")
        return

    data = rq.get(f"{graph}/oauth/access_token", params={
        'grant_type': 'fb_exchange_token',
        'client_id': app_id,
        'client_secret': app_secret,
        'fb_exchange_token': user_token,
    }, timeout=15).json()
    if 'error' in data:
        log.error(f"Token exchange failed: {data['error'].get('message')}")
        log.error("User tokens expire after ~1h - regenerate FACEBOOK_USER_TOKEN "
                  "in the Graph API Explorer and retry")
        return
    long_lived_user_token = data['access_token']

    pages = rq.get(f"{graph}/me/accounts",
                   params={'access_token': long_lived_user_token},
                   timeout=15).json()
    if 'error' in pages or not pages.get('data'):
        log.error(f"Could not list your Pages: {pages.get('error', {}).get('message', 'no pages found')}")
        log.error("Make sure the user token was generated with pages_show_list "
                  "and that your account manages the Page")
        return

    log.info("✅ Your Pages (page tokens from a long-lived user token don't expire):")
    for page in pages['data']:
        log.info(f"  {page['name']}")
        log.info(f"    FACEBOOK_PAGE_ID={page['id']}")
        log.info(f"    FACEBOOK_PAGE_ACCESS_TOKEN={page['access_token']}")
    log.info("Save the two values for Taraji Press in .env and as GitHub Actions "
             "secrets, then rerun this command to verify. FACEBOOK_APP_SECRET and "
             "FACEBOOK_USER_TOKEN can be removed from .env afterwards.")


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

    subparsers.add_parser('distribute', help='Send unpublished articles to all configured channels')
    subparsers.add_parser('telegram-setup', help='Verify bot token and list chat IDs')
    subparsers.add_parser('facebook-setup', help='Verify Page token or generate one (one-time)')
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
    elif args.command == 'facebook-setup':
        cmd_facebook_setup()
    elif args.command == 'stats':
        cmd_stats()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
