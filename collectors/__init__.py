"""
Collectors package for Taraji AI
"""
from .base_collector import BaseCollector
from .google_news import GoogleNewsCollector, collect_google_news
from .rss_collector import RSSCollector, collect_rss

__all__ = [
    'BaseCollector',
    'GoogleNewsCollector',
    'collect_google_news',
    'RSSCollector',
    'collect_rss',
]
