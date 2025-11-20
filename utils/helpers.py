"""
Utility helper functions for Taraji AI
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def load_json_config(filepath: str) -> Dict:
    """Load JSON configuration file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, filepath: str, indent: int = 2):
    """Save data to JSON file"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def get_timestamp(fmt: str = "%Y%m%d_%H%M%S") -> str:
    """Get current timestamp as formatted string"""
    return datetime.now().strftime(fmt)


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""

    # Remove extra whitespace
    text = ' '.join(text.split())

    # Remove special characters that cause issues
    text = text.replace('\x00', '')

    return text.strip()


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)].strip() + suffix


def parse_date(date_str: str) -> str:
    """Parse various date formats to ISO format"""
    from dateutil import parser

    try:
        dt = parser.parse(date_str)
        return dt.isoformat()
    except Exception:
        return datetime.now().isoformat()


def deduplicate_list(items: List[Any]) -> List[Any]:
    """Remove duplicates while preserving order"""
    seen = set()
    result = []

    for item in items:
        # For dictionaries, use URL as key
        key = item.get('url') if isinstance(item, dict) else item

        if key not in seen:
            seen.add(key)
            result.append(item)

    return result
