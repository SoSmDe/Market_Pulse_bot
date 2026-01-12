"""
SQLite база для хранения отправленных материалов.
Защита от дублей между дайджестами.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "data" / "market_pulse.db"


def get_connection() -> sqlite3.Connection:
    """Получить соединение с БД"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализация таблиц"""
    conn = get_connection()
    cursor = conn.cursor()

    # Таблица отправленных статей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            source TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица отправленных fundraising
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_fundraising (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            round_type TEXT,
            amount REAL,
            source_url TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(project, round_type)
        )
    """)

    # Индексы для быстрого поиска
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_url ON sent_articles(url)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_sent ON sent_articles(sent_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fundraising_project ON sent_fundraising(project)")

    conn.commit()
    conn.close()


def is_article_sent(url: str) -> bool:
    """Проверить, была ли статья уже отправлена"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM sent_articles WHERE url = ?", (url,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def is_fundraising_sent(project: str, round_type: str) -> bool:
    """Проверить, был ли fundraising уже отправлен"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM sent_fundraising WHERE project = ? AND round_type = ?",
        (project.lower(), round_type)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def mark_article_sent(url: str, title: str, source: str):
    """Пометить статью как отправленную"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO sent_articles (url, title, source) VALUES (?, ?, ?)",
            (url, title, source)
        )
        conn.commit()
    except Exception as e:
        print(f"DB error marking article: {e}")
    finally:
        conn.close()


def mark_fundraising_sent(project: str, round_type: str, amount: Optional[float], source_url: str):
    """Пометить fundraising как отправленный"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT OR IGNORE INTO sent_fundraising
               (project, round_type, amount, source_url) VALUES (?, ?, ?, ?)""",
            (project.lower(), round_type, amount, source_url)
        )
        conn.commit()
    except Exception as e:
        print(f"DB error marking fundraising: {e}")
    finally:
        conn.close()


def cleanup_old_records(days: int = 30):
    """Удалить старые записи (старше N дней)"""
    conn = get_connection()
    cursor = conn.cursor()
    cutoff = datetime.now() - timedelta(days=days)

    cursor.execute("DELETE FROM sent_articles WHERE sent_at < ?", (cutoff,))
    cursor.execute("DELETE FROM sent_fundraising WHERE sent_at < ?", (cutoff,))

    conn.commit()
    conn.close()

    print(f"Cleaned up records older than {days} days")


def get_stats() -> dict:
    """Получить статистику БД"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM sent_articles")
    articles_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM sent_fundraising")
    fundraising_count = cursor.fetchone()[0]

    conn.close()

    return {
        "articles": articles_count,
        "fundraising": fundraising_count
    }


# Инициализация при импорте
init_db()
