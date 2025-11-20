"""
Collectors package for Taraji AI
"""
from .base_collector import BaseCollector
from .google_news import GoogleNewsCollector, collect_google_news

__all__ = [
    'BaseCollector',
    'GoogleNewsCollector',
    'collect_google_news',
]
