"""
Base collector class for Taraji AI
"""
from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import datetime
import time

from utils import log, save_json, get_timestamp
from config import settings


class BaseCollector(ABC):
    """Abstract base class for all collectors"""

    def __init__(self, name: str):
        self.name = name
        self.stats = {
            'source': name,
            'collected': 0,
            'filtered': 0,
            'stored': 0,
            'errors': 0,
            'duration': 0,
        }

    @abstractmethod
    def collect(self) -> List[Dict]:
        """
        Collect articles from source
        Must be implemented by subclasses

        Returns:
            List of article dictionaries
        """
        pass

    def run(self) -> List[Dict]:
        """
        Run the collector with timing and error handling

        Returns:
            List of collected articles
        """
        log.info(f"Starting {self.name} collector")
        start_time = time.time()

        try:
            articles = self.collect()
            self.stats['collected'] = len(articles)

            # Save raw data
            self._save_raw_data(articles)

            log.info(f"{self.name}: Collected {len(articles)} articles")
            return articles

        except Exception as e:
            log.error(f"{self.name} collection failed: {e}", exc_info=True)
            self.stats['errors'] += 1
            return []

        finally:
            self.stats['duration'] = time.time() - start_time
            log.info(f"{self.name}: Completed in {self.stats['duration']:.2f}s")

    def _save_raw_data(self, articles: List[Dict]):
        """Save raw collected data to JSON file"""
        if not articles:
            return

        timestamp = get_timestamp()
        source_dir = settings.DATA_DIR / "raw" / self.name.lower().replace(' ', '_')
        source_dir.mkdir(parents=True, exist_ok=True)

        filepath = source_dir / f"{timestamp}.json"
        save_json(articles, str(filepath))
        log.debug(f"Saved raw data to {filepath}")

    def get_stats(self) -> Dict:
        """Get collection statistics"""
        return self.stats.copy()
