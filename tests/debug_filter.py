#!/usr/bin/env python3
"""
Debug script to see why articles are being filtered out
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from collectors import collect_google_news
from processors import create_keyword_filter
from utils import log

print("=" * 80)
print("DEBUGGING KEYWORD FILTER")
print("=" * 80)

# Collect articles
log.info("Collecting articles...")
articles = collect_google_news()

if not articles:
    print("❌ No articles collected!")
    sys.exit(1)

print(f"\n✅ Collected {len(articles)} articles")
print("\nSample article titles:")
print("-" * 80)

# Show first 10 article titles and descriptions
for i, article in enumerate(articles[:10], 1):
    title = article.get('title', 'No title')
    desc = article.get('description', 'No description')
    print(f"\n{i}. TITLE: {title}")
    print(f"   DESC: {desc[:150]}...")

# Now test the filter
print("\n" + "=" * 80)
print("TESTING KEYWORD FILTER")
print("=" * 80)

keyword_filter = create_keyword_filter()

# Test each article individually to see why it fails
for i, article in enumerate(articles[:10], 1):
    title = article.get('title', '')
    desc = article.get('description', '')
    text = f"{title} {desc}"

    print(f"\n{i}. Testing: {title[:80]}...")

    # Test the match
    matches, matched_keyword = keyword_filter.matches(text.lower(), 'unknown')

    if matches:
        print(f"   ✅ MATCHED: {matched_keyword}")
    else:
        print(f"   ❌ NO MATCH")
        # Check if it contains any of our keywords manually
        keywords_to_check = [
            'esperance', 'espérance', 'est tunis', 'taraji', 'الترجي'
        ]
        found = []
        for kw in keywords_to_check:
            if kw in text.lower():
                found.append(kw)

        if found:
            print(f"   ⚠️  BUT CONTAINS: {found}")
            print(f"   🔍 Might be filtered by NEGATIVE keywords!")

print("\n" + "=" * 80)
print("FILTER SUMMARY")
print("=" * 80)

filtered = keyword_filter.filter_articles(articles)
print(f"\nInput: {len(articles)} articles")
print(f"Output: {len(filtered)} articles")
print(f"Filtered out: {len(articles) - len(filtered)} articles")

if filtered:
    print("\n✅ Articles that PASSED:")
    for art in filtered[:5]:
        print(f"   • {art['title'][:80]}...")
        print(f"     Matched: {art.get('matched_keyword', 'Unknown')}")
