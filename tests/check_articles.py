#!/usr/bin/env python3
"""
Check sample articles from database to verify filtering
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage import get_db

print("=" * 80)
print("CHECKING DATABASE ARTICLES")
print("=" * 80)

with get_db() as db:
    cursor = db.conn.cursor()

    # Get total count
    cursor.execute("SELECT COUNT(*) FROM articles")
    total = cursor.fetchone()[0]
    print(f"\nTotal articles in database: {total}")

    # Get recent articles
    cursor.execute("""
        SELECT id, title, source, language, category, source_type, published_date
        FROM articles
        ORDER BY collected_date DESC
        LIMIT 30
    """)

    recent_articles = cursor.fetchall()

    print("\n" + "=" * 80)
    print("LAST 30 ARTICLES COLLECTED:")
    print("=" * 80)

    for i, article in enumerate(recent_articles, 1):
        print(f"\n{i}. Title: {article['title'][:100]}")
        print(f"   Source: {article['source']}")
        print(f"   Language: {article['language']}")
        print(f"   Category: {article['category']}")
        print(f"   Source Type: {article['source_type']}")
        print(f"   Published: {article['published_date']}")

    # Check by source
    print("\n" + "=" * 80)
    print("ARTICLES BY SOURCE:")
    print("=" * 80)

    cursor.execute("""
        SELECT source_type, COUNT(*) as count
        FROM articles
        GROUP BY source_type
        ORDER BY count DESC
    """)

    for row in cursor.fetchall():
        print(f"  {row['source_type']}: {row['count']} articles")

    # Check top sources
    print("\n" + "=" * 80)
    print("TOP SOURCES:")
    print("=" * 80)

    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM articles
        GROUP BY source
        ORDER BY count DESC
        LIMIT 15
    """)

    for row in cursor.fetchall():
        print(f"  {row['source']}: {row['count']} articles")
