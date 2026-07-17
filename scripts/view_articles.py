#!/usr/bin/env python3
"""View articles and summaries from the database"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage import get_db
from utils import log

log.info("=" * 80)
log.info("REAL ARTICLES WITH SUMMARIES FROM DATABASE")
log.info("=" * 80)

with get_db() as db:
    cursor = db.conn.cursor()

    # Get articles with summaries
    cursor.execute("""
        SELECT id, title, language, category, summary, url
        FROM articles
        WHERE summary IS NOT NULL AND length(summary) > 10
        ORDER BY id DESC
        LIMIT 10
    """)

    articles = cursor.fetchall()

    if not articles:
        log.warning("No articles with summaries found in database!")
    else:
        log.info(f"\nFound {len(articles)} articles with summaries:\n")

        for article in articles:
            article_id, title, language, category, summary, url = article

            log.info("=" * 80)
            log.info(f"ID: {article_id}")
            log.info(f"Title: {title}")
            log.info(f"Language: {language} | Category: {category}")
            log.info(f"URL: {url}")
            log.info("-" * 80)
            log.info(f"SUMMARY:\n{summary}")
            log.info("")
