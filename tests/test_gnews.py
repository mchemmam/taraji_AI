#!/usr/bin/env python3
"""
Debug script to test Google News API
"""
from gnews import GNews

print("Testing GNews library...")
print("=" * 60)

# Test with different time periods
periods = ["7d", "1d", "12h", "1h"]
queries = [
    "Esperance Tunis",
    "Espérance Tunis",
    "EST football Tunisia",
]

for period in periods:
    print(f"\n📅 Testing period: {period}")
    print("-" * 60)

    gnews = GNews(
        language='en',
        country='TN',
        period=period,
        max_results=10
    )

    for query in queries:
        print(f"\n🔍 Query: {query}")
        try:
            results = gnews.get_news(query)
            print(f"   ✅ Found {len(results)} articles")

            if results:
                # Show first result
                first = results[0]
                print(f"   📰 Sample: {first.get('title', 'No title')[:80]}...")
                print(f"   🔗 URL: {first.get('url', 'No URL')}")
                print(f"   📅 Published: {first.get('published date', 'Unknown')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("Testing complete!")
