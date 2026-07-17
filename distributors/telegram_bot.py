"""
Telegram distributor for Taraji AI.

Posts new articles to a Telegram chat/channel via the Bot API (plain HTTPS,
no SDK needed). The target chat comes from TELEGRAM_CHAT_ID so switching
from a test chat to the public channel is just a config change.
"""
import html
import os
import time
from typing import Dict, Optional

import requests

from utils import log
from config import settings


TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# Telegram allows ~20 messages/minute to the same chat
SECONDS_BETWEEN_MESSAGES = 3

# Photo captions have a much lower limit than text messages
CAPTION_MAX_LENGTH = 1024


class TelegramDistributor:
    """Send articles to a Telegram chat or channel"""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        # Test chat first; the public channel ID is kept separately until launch
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')

        if not self.bot_token or not self.chat_id:
            log.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing - distribution disabled")

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def _call(self, method: str, payload: Dict) -> Optional[Dict]:
        url = TELEGRAM_API.format(token=self.bot_token, method=method)
        try:
            response = requests.post(url, json=payload, timeout=15)
            data = response.json()
            if not data.get('ok'):
                log.error(f"Telegram API error ({method}): {data.get('description')}")
                return None
            return data.get('result')
        except Exception as e:
            log.error(f"Telegram request failed ({method}): {e}")
            return None

    def send_article(self, article: Dict) -> Optional[str]:
        """
        Post one article to the configured chat - as a photo with caption
        when the article has an image, as a plain text message otherwise
        (or when Telegram cannot fetch the image).

        Returns the Telegram message id on success, None on failure.
        """
        image_url = (article.get('image_url') or '').strip()
        if image_url.startswith('http'):
            result = self._call('sendPhoto', {
                'chat_id': self.chat_id,
                'photo': image_url,
                'caption': self.format_article(article, limit=CAPTION_MAX_LENGTH),
                'parse_mode': 'HTML',
            })
            if result:
                return str(result['message_id'])
            log.warning("sendPhoto failed - falling back to text-only message")

        result = self._call('sendMessage', {
            'chat_id': self.chat_id,
            'text': self.format_article(article),
            'parse_mode': 'HTML',
            'disable_web_page_preview': False,
        })
        return str(result['message_id']) if result else None

    def format_article(self, article: Dict, limit: int = None) -> str:
        """Format an article as a Telegram HTML message.

        Shows both the French and Arabic summaries when available. When the
        result exceeds `limit` (photo captions allow only 1024 chars), the
        summaries are trimmed first so the footer and link always survive.
        """
        limit = limit or settings.TELEGRAM_MAX_MESSAGE_LENGTH
        category = article.get('category') or 'other'
        cat_info = settings.CATEGORIES.get(category, settings.CATEGORIES['other'])
        emoji = cat_info['emoji']

        raw_title = article.get('title') or ''
        title = html.escape(raw_title)
        source = html.escape(article.get('source') or '')
        link = article.get('resolved_url') or article.get('url') or ''

        summaries = []
        for key in ('summary', 'summary_ar'):
            text = (article.get(key) or '').strip()
            if text and text not in raw_title:
                summaries.append(html.escape(text))

        def build(summary_blocks):
            lines = [f"{emoji} <b>{title}</b>"]
            for block in summary_blocks:
                lines.append("")
                lines.append(block)
            lines.append("")
            lines.append(f"📰 {source} | {cat_info['name_fr']} • {cat_info['name_ar']}")
            if link:
                lines.append(f'<a href="{html.escape(link)}">Lire l\'article</a>')
            return "\n".join(lines)

        message = build(summaries)
        while len(message) > limit and summaries:
            excess = len(message) - limit
            last = summaries[-1]
            if len(last) > excess + 20:
                summaries[-1] = last[:len(last) - excess - 1].rsplit(' ', 1)[0] + '…'
            else:
                summaries.pop()
            message = build(summaries)

        if len(message) > limit:
            # Pathological title; if the cut breaks the HTML, the send falls
            # back to a plain text message with the full 4096-char budget
            message = message[:limit - 1] + '…'
        return message

    def distribute(self, db) -> Dict:
        """
        Send all unpublished recent articles to the chat.

        Args:
            db: connected Database instance

        Returns:
            Stats dict with sent/failed counts.
        """
        stats = {'sent': 0, 'failed': 0}

        if not self.enabled:
            log.warning("Telegram distributor not configured - skipping")
            return stats

        articles = db.get_unpublished_articles()
        if not articles:
            log.info("No new articles to distribute")
            return stats

        log.info(f"Distributing {len(articles)} articles to Telegram chat {self.chat_id}")

        for article in articles:
            message_id = self.send_article(article)
            if message_id:
                db.mark_published(article['id'], 'telegram', message_id, 'success')
                stats['sent'] += 1
                log.info(f"  ✅ Sent: {article['title'][:70]}")
            else:
                db.mark_published(article['id'], 'telegram', None, 'failed')
                stats['failed'] += 1
                log.warning(f"  ❌ Failed: {article['title'][:70]}")

            time.sleep(SECONDS_BETWEEN_MESSAGES)

        log.info(f"Distribution complete: {stats['sent']} sent, {stats['failed']} failed")
        return stats

    def get_me(self) -> Optional[Dict]:
        """Verify the bot token (returns bot info or None)"""
        return self._call('getMe', {})


def create_telegram_distributor() -> TelegramDistributor:
    """Create Telegram distributor instance"""
    return TelegramDistributor()
