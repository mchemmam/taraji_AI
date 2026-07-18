"""
Facebook Page distributor for Taraji AI.

Posts new articles to the Taraji Press Facebook Page via the Graph API
(plain HTTPS, no SDK). Auth is a long-lived Page access token generated
once via `python main.py facebook-setup`; posting only to our own Page
needs no Facebook App Review.
"""
import os
import time
from typing import Dict, Optional

import requests

from utils import log
from config import settings
from processors.rival_guard import screen_articles


GRAPH_API = "https://graph.facebook.com/v23.0"

# Pages API rate limits are generous; a short pause keeps even a backlog
# flush well clear of them
SECONDS_BETWEEN_POSTS = 2


class FacebookDistributor:
    """Publish articles to a Facebook Page"""

    channel = 'facebook'

    def __init__(self, page_id: Optional[str] = None,
                 access_token: Optional[str] = None):
        self.page_id = page_id or os.getenv('FACEBOOK_PAGE_ID')
        self.access_token = access_token or os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')

        if not self.page_id or not self.access_token:
            log.warning("FACEBOOK_PAGE_ID or FACEBOOK_PAGE_ACCESS_TOKEN missing "
                        "- Facebook distribution disabled")

    @property
    def enabled(self) -> bool:
        return bool(self.page_id and self.access_token)

    def _call(self, endpoint: str, payload: Dict) -> Optional[Dict]:
        url = f"{GRAPH_API}/{endpoint}"
        try:
            response = requests.post(
                url, data={**payload, 'access_token': self.access_token},
                timeout=20,
            )
            data = response.json()
            if 'error' in data:
                error = data['error']
                log.error(f"Facebook API error ({endpoint}): "
                          f"{error.get('message')} (code {error.get('code')})")
                return None
            return data
        except Exception as e:
            log.error(f"Facebook request failed ({endpoint}): {e}")
            return None

    def send_article(self, article: Dict) -> Optional[str]:
        """
        Post one article to the Page - as a photo post when the article has
        an image, as a link post otherwise (or when Facebook cannot fetch
        the image).

        Returns the Facebook post id on success, None on failure.
        """
        link = article.get('resolved_url') or article.get('url') or ''
        image_url = (article.get('image_url') or '').strip()

        if image_url.startswith('http'):
            result = self._call(f"{self.page_id}/photos", {
                'url': image_url,
                'message': self.format_article(article, include_link=True),
            })
            if result:
                return result.get('post_id') or result.get('id')
            log.warning("Photo post failed - falling back to link post")

        payload = {'message': self.format_article(article)}
        if link:
            payload['link'] = link
        result = self._call(f"{self.page_id}/feed", payload)
        return result.get('id') if result else None

    def format_article(self, article: Dict, include_link: bool = False) -> str:
        """Format an article as a plain-text Facebook post.

        Link posts pass the URL separately (Facebook renders it as a preview
        card), so the text omits it; photo posts have no link field, so
        include_link=True appends the URL to the text instead.
        """
        category = article.get('category') or 'other'
        cat_info = settings.CATEGORIES.get(category, settings.CATEGORIES['other'])

        title = article.get('title') or ''
        source = article.get('source') or ''
        link = article.get('resolved_url') or article.get('url') or ''

        lines = [f"{cat_info['emoji']} {title}"]
        for key in ('summary', 'summary_ar'):
            text = (article.get(key) or '').strip()
            if text and text not in title:
                lines.append("")
                lines.append(text)
        lines.append("")
        lines.append(f"📰 {source} | {cat_info['name_fr']} • {cat_info['name_ar']}")
        if include_link and link:
            lines.append(link)
        return "\n".join(lines)

    def distribute(self, db) -> Dict:
        """
        Post all recent articles not yet published to Facebook.

        Args:
            db: connected Database instance

        Returns:
            Stats dict with sent/failed counts.
        """
        stats = {'sent': 0, 'failed': 0}

        if not self.enabled:
            log.warning("Facebook distributor not configured - skipping")
            return stats

        articles = db.get_unpublished_articles(channel=self.channel)
        # Last line of defense for the rival-club rule - also covers articles
        # that entered the database before the collection-time guard existed
        articles = screen_articles(db, articles, self.channel)
        if not articles:
            log.info("No new articles for Facebook")
            return stats

        log.info(f"Publishing {len(articles)} articles to Facebook Page {self.page_id}")

        for article in articles:
            post_id = self.send_article(article)
            if post_id:
                db.mark_published(article['id'], self.channel, post_id, 'success')
                stats['sent'] += 1
                log.info(f"  ✅ Posted: {article['title'][:70]}")
            else:
                db.mark_published(article['id'], self.channel, None, 'failed')
                stats['failed'] += 1
                log.warning(f"  ❌ Failed: {article['title'][:70]}")

            time.sleep(SECONDS_BETWEEN_POSTS)

        log.info(f"Facebook distribution complete: {stats['sent']} sent, {stats['failed']} failed")
        return stats

    def get_page(self) -> Optional[Dict]:
        """Verify the Page token (returns page id/name or None)"""
        try:
            data = requests.get(
                f"{GRAPH_API}/me",
                params={'fields': 'id,name', 'access_token': self.access_token},
                timeout=15,
            ).json()
        except Exception as e:
            log.error(f"Facebook request failed (me): {e}")
            return None
        if 'error' in data:
            log.error(f"Facebook API error (me): {data['error'].get('message')}")
            return None
        return data


def create_facebook_distributor() -> FacebookDistributor:
    """Create Facebook distributor instance"""
    return FacebookDistributor()
