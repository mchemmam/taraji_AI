"""
Database operations for Taraji AI
"""
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json

from config import settings


def _utcnow() -> datetime:
    """Naive UTC now, comparable to the DB's CURRENT_TIMESTAMP values.

    Every DEFAULT CURRENT_TIMESTAMP column stores naive UTC. datetime.now()
    only matched it because GitHub runners run on UTC; on a CEST laptop
    every recency window was silently shifted by two hours.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Database:
    """SQLite database manager for Taraji AI"""

    # collection_stats.source value marking a run-start heartbeat, kept
    # distinct so per-source stats could still be written alongside later
    HEARTBEAT_SOURCE = '__run__'

    # URLs the AI judged irrelevant/stale - remembered so the same article
    # is not re-extracted and re-judged on every scheduled run
    REJECTED_URLS_SCHEMA = """
        CREATE TABLE IF NOT EXISTS rejected_urls (
            url TEXT PRIMARY KEY,
            resolved_url TEXT,
            reason TEXT,
            rejected_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """

    # Per-publisher extraction health, driving both the circuit breaker and
    # the alert suppression. One row per domain, created on first failure.
    PUBLISHER_HEALTH_SCHEMA = """
        CREATE TABLE IF NOT EXISTS publisher_health (
            domain TEXT PRIMARY KEY,
            consecutive_failures INTEGER NOT NULL DEFAULT 0,
            last_reason TEXT,
            last_failure_date DATETIME,
            last_alert_date DATETIME
        )
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self.conn = None
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure data directory exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self._migrate()
        return self.conn

    def _migrate(self):
        """Apply lightweight schema migrations to existing databases"""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(articles)")
        columns = {row['name'] for row in cursor.fetchall()}
        if columns and 'resolved_url' not in columns:
            cursor.execute("ALTER TABLE articles ADD COLUMN resolved_url TEXT")
        if columns and 'summary_ar' not in columns:
            cursor.execute("ALTER TABLE articles ADD COLUMN summary_ar TEXT")
        # Groups every post about one running story (the original and each
        # later "Mise à jour") so updates can be rate-limited per story.
        # NULL on rows predating this column - callers fall back to the id,
        # which makes each old row its own story.
        if columns and 'story_key' not in columns:
            cursor.execute("ALTER TABLE articles ADD COLUMN story_key TEXT")
        cursor.execute(self.REJECTED_URLS_SCHEMA)
        cursor.execute(self.PUBLISHER_HEALTH_SCHEMA)
        # get_unpublished_articles probes distribution_log per article/channel
        if columns:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_distribution_article
                ON distribution_log(article_id, channel)
            """)
        self.conn.commit()

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.close()

    def initialize_schema(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()

        # Main articles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                source_type TEXT,
                published_date DATETIME,
                collected_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                language TEXT,
                category TEXT,
                content TEXT,
                summary TEXT,
                summary_ar TEXT,
                resolved_url TEXT,
                duplicate_of INTEGER,
                is_published BOOLEAN DEFAULT 0,

                author TEXT,
                image_url TEXT,

                retweets INTEGER,
                likes INTEGER,

                FOREIGN KEY (duplicate_of) REFERENCES articles(id)
            )
        """)

        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_published_date
            ON articles(published_date DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category
            ON articles(category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_language
            ON articles(language)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_collected_date
            ON articles(collected_date DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_is_published
            ON articles(is_published)
        """)

        # Keywords matched table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keywords_matched (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                match_type TEXT,
                FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_keywords_article
            ON keywords_matched(article_id)
        """)

        # Collection statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collection_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT NOT NULL,
                articles_collected INTEGER,
                articles_filtered INTEGER,
                articles_stored INTEGER,
                errors INTEGER,
                duration_seconds REAL
            )
        """)

        cursor.execute(self.REJECTED_URLS_SCHEMA)
        cursor.execute(self.PUBLISHER_HEALTH_SCHEMA)

        # Distribution log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS distribution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                channel TEXT NOT NULL,
                sent_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_id TEXT,
                status TEXT,
                FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_distribution_article
            ON distribution_log(article_id, channel)
        """)

        self.conn.commit()
        return True

    def insert_article(self, article: Dict) -> Optional[int]:
        """
        Insert a new article into the database
        Returns article_id if successful, None if duplicate
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO articles (
                    url, title, source, source_type, published_date,
                    language, category, content, summary, summary_ar,
                    resolved_url, author, image_url, retweets, likes,
                    story_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article.get('url'),
                article.get('title'),
                article.get('source'),
                article.get('source_type'),
                article.get('published_date'),
                article.get('language'),
                article.get('category'),
                article.get('content'),
                article.get('summary'),
                article.get('summary_ar'),
                article.get('resolved_url'),
                article.get('author'),
                article.get('image_url'),
                article.get('retweets'),
                article.get('likes'),
                article.get('story_key')
            ))

            article_id = cursor.lastrowid

            # Insert matched keyword if present
            matched_keyword = article.get('matched_keyword')
            if matched_keyword:
                self.insert_matched_keyword(article_id, matched_keyword)

            self.conn.commit()
            return article_id

        except sqlite3.IntegrityError:
            # Duplicate URL
            return None

    def insert_matched_keyword(self, article_id: int, keyword: str):
        """
        Insert a matched keyword for an article

        Args:
            article_id: Article ID
            keyword: The matched keyword (may include match type like "Taraji (contextual)")
        """
        cursor = self.conn.cursor()

        # Extract match type if present (e.g., "Taraji (contextual)" -> "contextual")
        match_type = "exact"
        if "(" in keyword and ")" in keyword:
            parts = keyword.rsplit("(", 1)
            keyword = parts[0].strip()
            match_type = parts[1].rstrip(")").strip()

        cursor.execute("""
            INSERT INTO keywords_matched (article_id, keyword, match_type)
            VALUES (?, ?, ?)
        """, (article_id, keyword, match_type))

        # Note: Don't commit here - let the calling method handle the transaction

    def get_existing_urls(self, urls: List[str]) -> set:
        """Return the subset of given URLs already seen - stored as articles
        or rejected (matched against collected and resolved URLs).

        Rejections whose verdict came from a judgment rather than a fact
        expire and get re-read: 'irrelevant' (one stochastic AI call),
        'unverified_date' (one publisher-feed snapshot) and
        'already_covered' (the "adds nothing new" half of it is a judgment,
        and it has buried the cancellation of a signing we had already
        announced). 'stale' and 'duplicate' are facts a re-run cannot
        change, so they stay permanent.
        """
        existing = set()
        cursor = self.conn.cursor()

        # reason -> hours after which the rejection stops hiding the URL
        ttl_by_reason = {
            ('irrelevant', 'unverified_date'):
                int(settings.IRRELEVANT_REJECTION_TTL_HOURS),
            ('already_covered',):
                int(settings.ALREADY_COVERED_REJECTION_TTL_HOURS),
        }
        chunk_size = 200
        for i in range(0, len(urls), chunk_size):
            chunk = urls[i:i + chunk_size]
            placeholders = ','.join('?' * len(chunk))
            for table in ('articles', 'rejected_urls'):
                not_expired = ""
                if table == 'rejected_urls':
                    # rejected_date is CURRENT_TIMESTAMP, i.e. UTC
                    not_expired = "".join(
                        f"""
                    AND NOT (reason IN ({','.join("'" + r + "'" for r in reasons)})
                             AND rejected_date < datetime('now', '-{hours} hours'))"""
                        for reasons, hours in ttl_by_reason.items()
                    )
                cursor.execute(f"""
                    SELECT url, resolved_url FROM {table}
                    WHERE (url IN ({placeholders}) OR resolved_url IN ({placeholders}))
                    {not_expired}
                """, chunk + chunk)
                for row in cursor.fetchall():
                    existing.add(row['url'])
                    if row['resolved_url']:
                        existing.add(row['resolved_url'])

        return existing

    def insert_rejected_url(self, url: str, resolved_url: str = None,
                            reason: str = None):
        """Remember a rejected URL so it is skipped on future runs.

        REPLACE (not IGNORE) so a re-rejection refreshes rejected_date:
        an expired-and-re-judged 'irrelevant' URL re-arms its TTL instead of
        being re-extracted and re-judged on every subsequent run.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO rejected_urls (url, resolved_url, reason)
            VALUES (?, ?, ?)
        """, (url, resolved_url, reason))
        self.conn.commit()

    def record_extraction_outcome(self, domain: str, ok: bool,
                                  reason: str = None) -> int:
        """Update a publisher's failure streak; return its new length.

        A success resets the streak to zero rather than decrementing it: a
        publisher that is serving again should get its full trip budget back
        before we stop fetching it, and the streak is only ever meant to
        answer "is this host down right now?".
        """
        if not domain:
            return 0
        cursor = self.conn.cursor()
        if ok:
            cursor.execute("""
                UPDATE publisher_health
                SET consecutive_failures = 0, last_reason = NULL
                WHERE domain = ?
            """, (domain,))
            self.conn.commit()
            return 0

        cursor.execute("""
            INSERT INTO publisher_health
                (domain, consecutive_failures, last_reason, last_failure_date)
            VALUES (?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(domain) DO UPDATE SET
                consecutive_failures = consecutive_failures + 1,
                last_reason = excluded.last_reason,
                last_failure_date = CURRENT_TIMESTAMP
        """, (domain, reason))
        row = cursor.execute(
            "SELECT consecutive_failures FROM publisher_health WHERE domain = ?",
            (domain,)
        ).fetchone()
        self.conn.commit()
        return row['consecutive_failures'] if row else 1

    def get_tripped_publishers(self) -> Dict[str, str]:
        """Domains whose circuit is open, as {domain: last failure reason}.

        Open means the streak reached EXTRACTION_CIRCUIT_TRIP *and* the last
        failure is recent. Letting the cooldown expire is what re-opens the
        domain for a probe - no separate half-open bookkeeping, because a
        failed probe simply stamps last_failure_date again.
        """
        cursor = self.conn.cursor()
        rows = cursor.execute("""
            SELECT domain, last_reason FROM publisher_health
            WHERE consecutive_failures >= ?
            AND last_failure_date > datetime('now', ?)
        """, (int(settings.EXTRACTION_CIRCUIT_TRIP),
              f'-{int(settings.EXTRACTION_CIRCUIT_COOLDOWN_HOURS)} hours')).fetchall()
        return {row['domain']: row['last_reason'] or 'unknown' for row in rows}

    def unalerted_publishers(self, domains) -> set:
        """Subset of `domains` not alerted about within the alert cooldown."""
        domains = set(domains)
        if not domains:
            return set()
        cursor = self.conn.cursor()
        placeholders = ','.join('?' * len(domains))
        rows = cursor.execute(f"""
            SELECT domain FROM publisher_health
            WHERE domain IN ({placeholders})
            AND last_alert_date > datetime('now', ?)
        """, list(domains) + [
            f'-{int(settings.EXTRACTION_ALERT_COOLDOWN_HOURS)} hours'
        ]).fetchall()
        return domains - {row['domain'] for row in rows}

    def mark_publishers_alerted(self, domains):
        """Start the alert cooldown for each domain named in an ops alert."""
        if not domains:
            return
        cursor = self.conn.cursor()
        cursor.executemany("""
            INSERT INTO publisher_health (domain, last_alert_date)
            VALUES (?, CURRENT_TIMESTAMP)
            ON CONFLICT(domain) DO UPDATE SET last_alert_date = CURRENT_TIMESTAMP
        """, [(domain,) for domain in domains])
        self.conn.commit()

    def get_unpublished_articles(self, channel: str = 'telegram',
                                 hours: int = 48, limit: int = 15) -> List[Dict]:
        """Get recent articles not yet successfully sent to the given channel.

        Tracked per channel via distribution_log (not the global is_published
        flag), so each channel catches up independently - Telegram posting an
        article doesn't hide it from Facebook. 'vetoed' rows (rival-club
        guard) are terminal like 'success'; only 'failed' sends are retried.
        """
        cursor = self.conn.cursor()
        cutoff = _utcnow() - timedelta(hours=hours)

        cursor.execute("""
            SELECT * FROM articles a
            WHERE a.collected_date >= ?
            AND a.duplicate_of IS NULL
            AND NOT EXISTS (
                SELECT 1 FROM distribution_log dl
                WHERE dl.article_id = a.id
                AND dl.channel = ?
                AND dl.status IN ('success', 'vetoed')
            )
            ORDER BY a.collected_date ASC
            LIMIT ?
        """, (cutoff, channel, limit))

        return [dict(row) for row in cursor.fetchall()]

    def mark_published(self, article_id: int, channel: str,
                       message_id: str = None, status: str = 'success'):
        """Mark an article as published and log the distribution"""
        cursor = self.conn.cursor()
        if status == 'success':
            cursor.execute(
                "UPDATE articles SET is_published = 1 WHERE id = ?", (article_id,)
            )
        cursor.execute("""
            INSERT INTO distribution_log (article_id, channel, message_id, status)
            VALUES (?, ?, ?, ?)
        """, (article_id, channel, message_id, status))
        self.conn.commit()

    def get_article_by_url(self, url: str) -> Optional[Dict]:
        """Get article by URL"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE url = ?", (url,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_recent_articles(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """Get articles from the last N hours"""
        cursor = self.conn.cursor()
        cutoff = _utcnow() - timedelta(hours=hours)

        cursor.execute("""
            SELECT * FROM articles
            WHERE collected_date >= ?
            AND duplicate_of IS NULL
            ORDER BY collected_date DESC
            LIMIT ?
        """, (cutoff, limit))

        return [dict(row) for row in cursor.fetchall()]

    def get_articles_by_category(self, category: str, days: int = 7) -> List[Dict]:
        """Get articles by category from the last N days"""
        cursor = self.conn.cursor()
        cutoff = _utcnow() - timedelta(days=days)

        cursor.execute("""
            SELECT * FROM articles
            WHERE category = ?
            AND collected_date >= ?
            AND duplicate_of IS NULL
            ORDER BY collected_date DESC
        """, (category, cutoff))

        return [dict(row) for row in cursor.fetchall()]

    def mark_as_duplicate(self, article_id: int, original_id: int):
        """Mark an article as duplicate of another"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE articles
            SET duplicate_of = ?
            WHERE id = ?
        """, (original_id, article_id))
        self.conn.commit()

    def get_stats_summary(self) -> Dict:
        """Get database statistics"""
        cursor = self.conn.cursor()

        # Total articles
        cursor.execute("SELECT COUNT(*) as total FROM articles")
        total = cursor.fetchone()['total']

        # Articles last 24h
        cutoff_24h = _utcnow() - timedelta(hours=24)
        cursor.execute("""
            SELECT COUNT(*) as count FROM articles
            WHERE collected_date >= ?
        """, (cutoff_24h,))
        last_24h = cursor.fetchone()['count']

        # Articles last 7 days
        cutoff_7d = _utcnow() - timedelta(days=7)
        cursor.execute("""
            SELECT COUNT(*) as count FROM articles
            WHERE collected_date >= ?
        """, (cutoff_7d,))
        last_7days = cursor.fetchone()['count']

        # By category (last 7 days)
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM articles
            WHERE collected_date >= ?
            AND duplicate_of IS NULL
            GROUP BY category
        """, (cutoff_7d,))
        by_category = {row['category']: row['count'] for row in cursor.fetchall()}

        # By language (last 7 days)
        cursor.execute("""
            SELECT language, COUNT(*) as count
            FROM articles
            WHERE collected_date >= ?
            GROUP BY language
        """, (cutoff_7d,))
        by_language = {row['language']: row['count'] for row in cursor.fetchall()}

        return {
            'total_articles': total,
            'last_24h': last_24h,
            'last_7days': last_7days,
            'by_category': by_category,
            'by_language': by_language,
        }

    def insert_collection_stat(self, stat: Dict):
        """Insert collection statistics"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO collection_stats (
                source, articles_collected, articles_filtered,
                articles_stored, errors, duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            stat['source'],
            stat['collected'],
            stat['filtered'],
            stat['stored'],
            stat['errors'],
            stat['duration']
        ))
        self.conn.commit()

    def record_run_heartbeat(self) -> Optional[float]:
        """Stamp this run's start into collection_stats; return the gap.

        The gap is minutes since the previous run started, and it is the
        only evidence we have that the external 15-minute trigger
        (cron-job.org) is still alive: when it stops, no run fails and no
        alert fires anywhere, the pipeline just drops to whatever fraction
        of its cron slots GitHub feels like honouring.

        Returns None when there is no previous heartbeat - a fresh deploy,
        or the first run after this shipped. Callers must not read that as
        a zero gap; there is nothing to compare against yet.
        """
        cursor = self.conn.cursor()
        row = cursor.execute("""
            SELECT MAX(timestamp) FROM collection_stats WHERE source = ?
        """, (self.HEARTBEAT_SOURCE,)).fetchone()
        previous = row[0] if row else None

        cursor.execute("INSERT INTO collection_stats (source) VALUES (?)",
                       (self.HEARTBEAT_SOURCE,))
        self.conn.commit()

        if not previous:
            return None
        try:
            # DEFAULT CURRENT_TIMESTAMP writes naive UTC, so this compares
            # like-for-like against _utcnow() on a CEST laptop too
            last = datetime.fromisoformat(previous)
        except (TypeError, ValueError):
            return None
        return (_utcnow() - last).total_seconds() / 60

    def prune_old_data(self, days: int = 30) -> Tuple[int, int]:
        """Blank bulky article text and drop stale rejected URLs.

        Full article content is only needed once, to generate the summary at
        collection time. Blanking it after `days` caps the growth of the
        committed database while keeping every row (title, summary, category,
        URL, dates) for the future archive/dashboard. Rejected URLs only
        matter while an article can still reappear in the collection window,
        so old ones are dropped entirely.

        Returns (articles_pruned, rejected_urls_dropped).
        """
        cursor = self.conn.cursor()
        cutoff = _utcnow() - timedelta(days=days)

        cursor.execute("""
            UPDATE articles
            SET content = NULL
            WHERE collected_date < ?
            AND content IS NOT NULL
            AND summary IS NOT NULL
        """, (cutoff,))
        articles_pruned = cursor.rowcount

        cursor.execute("""
            DELETE FROM rejected_urls
            WHERE rejected_date < ?
        """, (cutoff,))
        rejected_dropped = cursor.rowcount

        # Publishers that recovered and have been quiet since carry no state
        # worth keeping. Rows with a live streak stay, however old, so an
        # open circuit is never silently reset by a pruning pass.
        cursor.execute("""
            DELETE FROM publisher_health
            WHERE consecutive_failures = 0
            AND (last_failure_date IS NULL OR last_failure_date < ?)
            AND (last_alert_date IS NULL OR last_alert_date < ?)
        """, (cutoff, cutoff))

        # Heartbeats have their own, much shorter retention - they arrive
        # ~200x a day and only serve the cadence watchdog
        cursor.execute("""
            DELETE FROM collection_stats
            WHERE source = ? AND timestamp < ?
        """, (self.HEARTBEAT_SOURCE,
              _utcnow() - timedelta(days=settings.RUN_HEARTBEAT_RETENTION_DAYS)))

        self.conn.commit()
        return articles_pruned, rejected_dropped

    def cleanup_old_articles(self, days: int = 90):
        """Delete articles older than N days"""
        cursor = self.conn.cursor()
        cutoff = _utcnow() - timedelta(days=days)

        cursor.execute("""
            DELETE FROM articles
            WHERE collected_date < ?
        """, (cutoff,))

        deleted = cursor.rowcount
        self.conn.commit()

        return deleted

    def vacuum(self):
        """Optimize database (reclaim space)"""
        cursor = self.conn.cursor()
        cursor.execute("VACUUM")
        self.conn.commit()


# Convenience functions
def get_db() -> Database:
    """Get database instance"""
    return Database()


def init_database():
    """Initialize database schema"""
    with get_db() as db:
        db.initialize_schema()
        print(f"✅ Database initialized at: {db.db_path}")
