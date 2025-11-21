"""
Database operations for Taraji AI
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json

from config import settings


class Database:
    """SQLite database manager for Taraji AI"""

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
        return self.conn

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
                    language, category, content, summary,
                    author, image_url, retweets, likes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                article.get('author'),
                article.get('image_url'),
                article.get('retweets'),
                article.get('likes')
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
        cutoff = datetime.now() - timedelta(hours=hours)

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
        cutoff = datetime.now() - timedelta(days=days)

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
        cutoff_24h = datetime.now() - timedelta(hours=24)
        cursor.execute("""
            SELECT COUNT(*) as count FROM articles
            WHERE collected_date >= ?
        """, (cutoff_24h,))
        last_24h = cursor.fetchone()['count']

        # Articles last 7 days
        cutoff_7d = datetime.now() - timedelta(days=7)
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

    def cleanup_old_articles(self, days: int = 90):
        """Delete articles older than N days"""
        cursor = self.conn.cursor()
        cutoff = datetime.now() - timedelta(days=days)

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
