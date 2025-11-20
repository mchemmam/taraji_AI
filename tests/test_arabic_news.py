#!/usr/bin/env python3
"""
Test different Google News libraries with Arabic queries
to find which one works best for Arabic content
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("TESTING ARABIC NEWS COLLECTION")
print("=" * 80)

# Test queries
arabic_queries = [
    "الترجي الرياضي التونسي",
    "الترجي التونسي",
    "الترجي",
    "Espérance Sportive de Tunis",  # Control - we know this works
]

print("\nTest queries:")
for i, q in enumerate(arabic_queries, 1):
    print(f"  {i}. {q}")

print("\n" + "=" * 80)
print("TEST 1: Current library (gnews)")
print("=" * 80)

try:
    from gnews import GNews

    for query in arabic_queries:
        print(f"\n🔍 Query: {query}")

        # Try different configurations
        configs = [
            {'language': 'ar', 'country': 'TN'},
            {'language': 'en', 'country': 'TN'},
            {'language': 'ar', 'country': 'SA'},  # Saudi Arabia (bigger Arabic market)
        ]

        for i, config in enumerate(configs, 1):
            print(f"   Config {i}: language={config['language']}, country={config['country']}")
            try:
                gnews = GNews(
                    language=config['language'],
                    country=config['country'],
                    period='7d',
                    max_results=5
                )
                results = gnews.get_news(query)

                if results:
                    print(f"      ✅ Found {len(results)} results")
                    if results:
                        print(f"      Sample: {results[0].get('title', 'No title')[:80]}")
                else:
                    print(f"      ❌ No results")
            except Exception as e:
                print(f"      ❌ Error: {e}")

except ImportError:
    print("❌ gnews not installed")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("TEST 2: pygooglenews library")
print("=" * 80)

try:
    from pygooglenews import GoogleNews

    for query in arabic_queries:
        print(f"\n🔍 Query: {query}")

        try:
            gn = GoogleNews(lang='ar', country='TN')
            results = gn.search(query)

            if results and 'entries' in results:
                entries = results['entries']
                print(f"   ✅ Found {len(entries)} results")
                if entries:
                    print(f"   Sample: {entries[0].get('title', 'No title')[:80]}")
            else:
                print(f"   ❌ No results")
        except Exception as e:
            print(f"   ❌ Error: {e}")

except ImportError:
    print("⚠️  pygooglenews not installed (pip install pygooglenews)")
    print("   Skipping this test...")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("TEST 3: Direct RSS from Google News")
print("=" * 80)

try:
    import feedparser

    for query in arabic_queries:
        print(f"\n🔍 Query: {query}")

        # Google News RSS URL format
        # We'll try different language/region combinations
        urls = [
            f"https://news.google.com/rss/search?q={query}&hl=ar&gl=TN&ceid=TN:ar",
            f"https://news.google.com/rss/search?q={query}&hl=ar&gl=SA&ceid=SA:ar",
            f"https://news.google.com/rss/search?q={query}&hl=fr&gl=TN&ceid=TN:fr",
        ]

        for i, url in enumerate(urls, 1):
            lang = url.split('hl=')[1].split('&')[0]
            country = url.split('gl=')[1].split('&')[0]
            print(f"   Config {i}: hl={lang}, gl={country}")

            try:
                feed = feedparser.parse(url)

                if feed.entries:
                    print(f"      ✅ Found {len(feed.entries)} results")
                    if feed.entries:
                        print(f"      Sample: {feed.entries[0].title[:80]}")
                else:
                    print(f"      ❌ No results")
            except Exception as e:
                print(f"      ❌ Error: {e}")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\nIf any test showed ✅ results for Arabic queries, we found a solution!")
print("Otherwise, we should implement RSS feeds from Arabic news sites.")
