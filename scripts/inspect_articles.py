#!/usr/bin/env python3
"""
Interactive article inspector - check individual articles for relevance
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage import get_db
from utils import log

def show_article(article_id):
    """Show full details of an article"""
    with get_db() as db:
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT id, url, title, source, source_type, published_date,
                   collected_date, language, category, content, summary,
                   author, image_url
            FROM articles
            WHERE id = ?
        """, (article_id,))

        article = cursor.fetchone()

        if not article:
            print(f"❌ Article {article_id} not found!")
            return

        print("=" * 80)
        print(f"ARTICLE #{article['id']}")
        print("=" * 80)
        print(f"Title:      {article['title']}")
        print(f"Source:     {article['source']} ({article['source_type']})")
        print(f"Language:   {article['language']}")
        print(f"Category:   {article['category']}")
        print(f"Published:  {article['published_date']}")
        print(f"Collected:  {article['collected_date']}")
        if article['author']:
            print(f"Author:     {article['author']}")
        print(f"URL:        {article['url'][:100]}...")
        print()
        print("-" * 80)
        print("SUMMARY:")
        print("-" * 80)
        print(article['summary'] if article['summary'] else "(No summary)")
        print()

        if article['content']:
            print("-" * 80)
            print(f"CONTENT ({len(article['content'])} chars):")
            print("-" * 80)
            print(article['content'][:500] + "..." if len(article['content']) > 500 else article['content'])
        else:
            print("(No content extracted)")

        print()
        print("=" * 80)

def list_recent(limit=20):
    """List recent articles with IDs"""
    with get_db() as db:
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT id, title, source, language, category
            FROM articles
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        articles = cursor.fetchall()

        print("=" * 80)
        print(f"RECENT {limit} ARTICLES")
        print("=" * 80)
        for article in articles:
            lang_emoji = {"ar": "🇹🇳", "fr": "🇫🇷", "en": "🇬🇧"}.get(article['language'], "🌍")
            print(f"{article['id']:3d}. {lang_emoji} [{article['category']:8s}] {article['title'][:60]}")
        print("=" * 80)
        print(f"\nTo inspect an article: python scripts/inspect_articles.py <id>")
        print(f"Example: python scripts/inspect_articles.py 191")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            article_id = int(sys.argv[1])
            show_article(article_id)
        except ValueError:
            print(f"❌ Invalid article ID: {sys.argv[1]}")
            print("Usage: python scripts/inspect_articles.py <article_id>")
    else:
        list_recent()
