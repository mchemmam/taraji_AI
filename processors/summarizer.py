"""
Article summarizer for Taraji AI using Google Gemini API with extractive fallback
"""
import os
import time
from typing import Optional
from datetime import datetime, timedelta

import google.generativeai as genai
from utils import log


class Summarizer:
    """
    Summarize articles using Google Gemini API with fallback to extractive summarization
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the summarizer

        Args:
            api_key: Google Gemini API key (if None, reads from env)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')

        if not self.api_key:
            log.warning("No Gemini API key found - will use extractive summarization only")
            self.model = None
        else:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.5-flash')  # Latest stable fast model
                log.info("Gemini API initialized successfully")
            except Exception as e:
                log.error(f"Failed to initialize Gemini API: {e}")
                self.model = None

        # Rate limiting tracking
        self.requests_today = 0
        self.last_request_time = None
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Limits (Gemini free tier)
        self.MAX_REQUESTS_PER_DAY = 1500
        self.MAX_REQUESTS_PER_MINUTE = 15
        self.MIN_REQUEST_INTERVAL = 60 / self.MAX_REQUESTS_PER_MINUTE  # 4 seconds

        # Track requests in last minute
        self.recent_requests = []

    def summarize(
        self,
        title: str,
        content: str,
        language: str = 'fr',
        max_sentences: int = 3
    ) -> Optional[str]:
        """
        Summarize an article using Gemini API, with fallback to extractive summarization

        Args:
            title: Article title
            content: Article content
            language: Article language (fr, ar, en, etc.)
            max_sentences: Maximum sentences for summary (for extractive fallback)

        Returns:
            Summary text or None if failed
        """
        # Try Gemini API first
        if self.model and self._can_make_request():
            try:
                summary = self._gemini_summarize(title, content, language)
                if summary:
                    self._track_request()
                    log.debug(f"✅ Gemini summarization successful (lang: {language})")
                    return summary
            except Exception as e:
                log.warning(f"Gemini API failed: {e}, falling back to extractive summarization")

        # Fallback to extractive summarization
        summary = self._extractive_summarize(content, max_sentences)
        log.debug(f"Using extractive summarization (lang: {language})")
        return summary

    def _can_make_request(self) -> bool:
        """
        Check if we can make another API request based on rate limits

        Returns:
            True if request is allowed, False otherwise
        """
        now = datetime.now()

        # Reset daily counter at midnight
        if now >= self.daily_reset_time + timedelta(days=1):
            self.requests_today = 0
            self.daily_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            self.recent_requests = []

        # Check daily limit
        if self.requests_today >= self.MAX_REQUESTS_PER_DAY:
            log.warning(f"Daily Gemini API limit reached ({self.MAX_REQUESTS_PER_DAY} requests)")
            return False

        # Clean up old requests (older than 1 minute)
        one_minute_ago = now - timedelta(seconds=60)
        self.recent_requests = [t for t in self.recent_requests if t > one_minute_ago]

        # Check per-minute limit
        if len(self.recent_requests) >= self.MAX_REQUESTS_PER_MINUTE:
            log.debug(f"Per-minute limit reached, waiting...")
            return False

        # Check minimum interval between requests
        if self.last_request_time:
            time_since_last = (now - self.last_request_time).total_seconds()
            if time_since_last < self.MIN_REQUEST_INTERVAL:
                sleep_time = self.MIN_REQUEST_INTERVAL - time_since_last
                log.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)

        return True

    def _track_request(self):
        """Track that a request was made for rate limiting"""
        now = datetime.now()
        self.last_request_time = now
        self.recent_requests.append(now)
        self.requests_today += 1

    def _gemini_summarize(self, title: str, content: str, language: str) -> Optional[str]:
        """
        Summarize using Gemini API

        Args:
            title: Article title
            content: Article content
            language: Article language

        Returns:
            Summary or None if failed
        """
        # Build prompt based on language
        prompts = {
            'fr': f"""Résume cet article de sport en français en 2-3 phrases maximum.
Concentre-toi sur les faits importants concernant l'Espérance Sportive de Tunis.

Titre: {title}

Contenu: {content[:2000]}

Résumé (2-3 phrases):""",

            'ar': f"""لخص هذا المقال الرياضي بالعربية في 2-3 جمل كحد أقصى.
ركز على الحقائق المهمة المتعلقة بالترجي الرياضي التونسي.

العنوان: {title}

المحتوى: {content[:2000]}

الملخص (2-3 جمل):""",

            'en': f"""Summarize this sports article in English in 2-3 sentences maximum.
Focus on the important facts concerning Espérance Sportive de Tunis.

Title: {title}

Content: {content[:2000]}

Summary (2-3 sentences):""",
        }

        # Default to French if language not supported
        prompt = prompts.get(language, prompts['fr'])

        try:
            response = self.model.generate_content(prompt)
            summary = response.text.strip()

            # Validate summary
            if summary and len(summary) > 10:
                return summary
            else:
                log.warning(f"Gemini returned short/empty summary: {summary}")
                return None

        except Exception as e:
            log.error(f"Gemini API error: {e}")
            raise

    def _extractive_summarize(self, content: str, max_sentences: int = 3) -> str:
        """
        Simple extractive summarization (fallback method)

        Takes the first N sentences from the content

        Args:
            content: Article content
            max_sentences: Number of sentences to extract

        Returns:
            Extracted summary
        """
        if not content:
            return ""

        # Clean content
        content = content.strip()

        # Split by sentence boundaries (., !, ?)
        # Simple approach - can be improved with NLTK
        sentences = []
        current = []

        for char in content:
            current.append(char)
            if char in '.!?' and len(current) > 20:  # Avoid splitting on abbreviations
                sentence = ''.join(current).strip()
                if sentence:
                    sentences.append(sentence)
                current = []
                if len(sentences) >= max_sentences:
                    break

        # Join first N sentences
        summary = ' '.join(sentences[:max_sentences])

        # Limit length
        if len(summary) > 500:
            summary = summary[:497] + '...'

        return summary

    def get_stats(self) -> dict:
        """
        Get current rate limiting statistics

        Returns:
            Dictionary with stats
        """
        return {
            'requests_today': self.requests_today,
            'daily_limit': self.MAX_REQUESTS_PER_DAY,
            'requests_last_minute': len(self.recent_requests),
            'per_minute_limit': self.MAX_REQUESTS_PER_MINUTE,
            'gemini_available': self.model is not None,
        }


# Singleton instance
_summarizer_instance = None


def create_summarizer() -> Summarizer:
    """
    Create or get singleton summarizer instance

    Returns:
        Summarizer instance
    """
    global _summarizer_instance

    if _summarizer_instance is None:
        _summarizer_instance = Summarizer()

    return _summarizer_instance


def summarize_article(title: str, content: str, language: str = 'fr') -> Optional[str]:
    """
    Convenience function to summarize an article

    Args:
        title: Article title
        content: Article content
        language: Article language

    Returns:
        Summary or None
    """
    summarizer = create_summarizer()
    return summarizer.summarize(title, content, language)
