"""
Article classifier for Taraji AI
Categorizes articles into: match, transfer, injury, statement, finance, other
"""
from typing import Optional
from utils import log
from config import settings


class ArticleClassifier:
    """Classify articles into categories based on content"""

    def __init__(self):
        self.categories = settings.CATEGORIES
        log.info(f"ArticleClassifier initialized with {len(self.categories)} categories")

    def classify(self, title: str, content: str = "") -> str:
        """
        Classify an article based on title and content

        Args:
            title: Article title
            content: Article content (optional)

        Returns:
            Category name (match, transfer, injury, statement, finance, other)
        """
        if not title:
            return 'other'

        # Combine title and content for analysis
        text = f"{title} {content}".lower()

        # Score each category
        scores = {}
        for category, data in self.categories.items():
            if category == 'other':
                continue

            keywords = data.get('keywords', [])
            score = 0

            for keyword in keywords:
                if keyword.lower() in text:
                    score += 1

            scores[category] = score

        # Return category with highest score, or 'other' if all zero
        if not scores or max(scores.values()) == 0:
            return 'other'

        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]

        log.debug(f"Classified as '{best_category}' (score: {best_score}): {title[:50]}...")
        return best_category

    def classify_batch(self, articles: list) -> list:
        """
        Classify multiple articles

        Args:
            articles: List of article dicts with 'title' and 'content'

        Returns:
            List of articles with 'category' field added
        """
        for article in articles:
            title = article.get('title', '')
            content = article.get('content', '') or article.get('summary', '') or ''

            category = self.classify(title, content)
            article['category'] = category

        return articles

    def get_category_info(self, category: str, language: str = 'en') -> dict:
        """
        Get category information (name, emoji)

        Args:
            category: Category key
            language: Language code (fr, ar, en)

        Returns:
            Dict with name and emoji
        """
        if category not in self.categories:
            return {'name': 'Other', 'emoji': '📰'}

        cat_data = self.categories[category]
        name_key = f'name_{language}'

        return {
            'name': cat_data.get(name_key, cat_data.get('name_en', category)),
            'emoji': cat_data.get('emoji', '📰')
        }


# Convenience function
def create_classifier() -> ArticleClassifier:
    """Create article classifier instance"""
    return ArticleClassifier()
