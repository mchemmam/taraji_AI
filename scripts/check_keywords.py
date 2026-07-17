#!/usr/bin/env python3
"""
Check how the keyword filter treats a given text.

Usage:
    python scripts/check_keywords.py "Some headline to test"
    python scripts/check_keywords.py            # runs built-in examples
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from processors import create_keyword_filter

EXAMPLES = [
    "Mercato: Elias Mokwana set for a comeback at Espérance de Tunis",
    "L'Espérance de Tunis remporte le derby face au Club Africain",
    "L'Espérance de Zarzis s'impose face à l'US Monastir",
    "الترجي يفوز في الدربي",
    "الترجي الجرجيسي يتعادل مع النجم الساحلي",
    "Taraji P. Henson stars in new drama series",
]


def check(kf, text):
    matches, keyword = kf.matches(text, 'unknown')
    verdict = f"✅ MATCH ({keyword})" if matches else "❌ NO MATCH"
    print(f"{verdict}\n   {text}\n")


if __name__ == '__main__':
    kf = create_keyword_filter()
    print("=" * 80)

    if len(sys.argv) > 1:
        check(kf, ' '.join(sys.argv[1:]))
    else:
        for example in EXAMPLES:
            check(kf, example)
