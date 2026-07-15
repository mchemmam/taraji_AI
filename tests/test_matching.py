#!/usr/bin/env python3
"""
Simple test to check keyword matching
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from processors import create_keyword_filter

# Test text from the actual article
test_text = "Mercato: Elias Mokwana set for a comeback at Espérance de Tunis Foot Africa"

print("=" * 80)
print("TESTING KEYWORD MATCHING")
print("=" * 80)
print(f"\nTest text: {test_text}")
print()

# Create filter
kf = create_keyword_filter()

# Test matching
matches, keyword = kf.matches(test_text, 'unknown')

print(f"Result: {'✅ MATCH' if matches else '❌ NO MATCH'}")
if keyword:
    print(f"Matched keyword: {keyword}")

# Also test lowercase
print("\n" + "-" * 80)
print("Testing with lowercase:")
matches2, keyword2 = kf.matches(test_text.lower(), 'unknown')
print(f"Result: {'✅ MATCH' if matches2 else '❌ NO MATCH'}")
if keyword2:
    print(f"Matched keyword: {keyword2}")

# Check if keyword is in text
print("\n" + "-" * 80)
print("Manual check - does text contain our keywords?")
keywords_to_check = [
    'espérance de tunis',
    'esperance de tunis',
    'espérance tunis',
    'esperance tunis',
]

text_lower = test_text.lower()
for kw in keywords_to_check:
    if kw in text_lower:
        print(f"  ✅ Found: '{kw}'")
    else:
        print(f"  ❌ Not found: '{kw}'")
