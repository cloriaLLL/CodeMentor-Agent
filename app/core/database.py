"""CodeMentor Agent - SQLite database manager for learning state persistence.

Provides async-friendly SQLite access with connection pooling and schema management.
All learning sessions, progress, exercise submissions, and problem cache are stored here.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from app.core.config import BASE_DIR
from app.core.logger import get_logger

logger = get_logger(__name__)

DB_PATH = BASE_DIR / "data" / "codementor.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS learning_sessions (
    session_id    TEXT PRIMARY KEY,
    user_id       TEXT DEFAULT 'default',
    topic         TEXT NOT NULL,
    phase         TEXT DEFAULT 'conversation',
    teaching_step INTEGER DEFAULT 0,
    context       TEXT DEFAULT '{}',
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS learning_progress (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    knowledge_point TEXT NOT NULL,
    status          TEXT DEFAULT 'not_started',
    mastery_score   INTEGER DEFAULT 0,
    attempts        INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES learning_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS exercise_submissions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT,
    exercise_id     TEXT NOT NULL,
    exercise_type   TEXT NOT NULL,
    exercise_subtype TEXT,
    user_answer     TEXT,
    result          TEXT,
    score           INTEGER DEFAULT 0,
    feedback        TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS problem_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT NOT NULL,
    source_id   TEXT,
    title       TEXT NOT NULL,
    difficulty  TEXT,
    description TEXT,
    starter_code TEXT,
    test_cases  TEXT,
    tags        TEXT,
    fetched_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(source, source_id)
);

CREATE INDEX IF NOT EXISTS idx_progress_session ON learning_progress(session_id);
CREATE INDEX IF NOT EXISTS idx_submissions_session ON exercise_submissions(session_id);
CREATE INDEX IF NOT EXISTS idx_problem_tags ON problem_cache(tags);

-- Conversation storage (对话存储层)
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id  TEXT PRIMARY KEY,
    user_id          TEXT DEFAULT 'default',
    type             TEXT NOT NULL,
    title            TEXT DEFAULT '',
    parent_id        TEXT,
    module_key       TEXT,
    summary          TEXT DEFAULT '',
    meta             TEXT DEFAULT '{}',
    message_count    INTEGER DEFAULT 0,
    created_at       TEXT DEFAULT (datetime('now')),
    updated_at       TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (parent_id) REFERENCES conversations(conversation_id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_conv_module_unique ON conversations(module_key) WHERE module_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_conv_parent ON conversations(parent_id);
CREATE INDEX IF NOT EXISTS idx_conv_type ON conversations(type);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id  TEXT NOT NULL,
    role             TEXT NOT NULL,
    content          TEXT NOT NULL,
    msg_meta         TEXT DEFAULT '{}',
    seq              INTEGER NOT NULL,
    created_at       TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_msg_conv ON conversation_messages(conversation_id, seq);
"""


class DatabaseManager:
    """Thread-safe SQLite database manager with lazy initialization."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or DB_PATH
        self._local = threading.local()
        self._initialized = False

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local connection."""
        if not hasattr(self._local, "conn"):
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    def init_db(self) -> None:
        """Initialize database schema (idempotent)."""
        if self._initialized:
            return
        conn = self._get_conn()
        conn.executescript(_SCHEMA)
        conn.commit()
        self._initialized = True
        logger.info("database_initialized", path=str(self._db_path))

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single SQL statement."""
        conn = self._get_conn()
        cur = conn.execute(sql, params)
        conn.commit()
        return cur

    def query_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Query a single row."""
        conn = self._get_conn()
        return conn.execute(sql, params).fetchone()

    def query_all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Query multiple rows."""
        conn = self._get_conn()
        return conn.execute(sql, params).fetchall()

    def upsert(self, table: str, data: dict[str, Any], conflict_col: str) -> None:
        """Insert or update a row."""
        cols = list(data.keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c != conflict_col)
        sql = (
            f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) "
            f"ON CONFLICT({conflict_col}) DO UPDATE SET {updates}"
        ) if updates else (
            f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"
        )
        conn = self._get_conn()
        conn.execute(sql, tuple(data.values()))
        conn.commit()


_db_manager: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """Get cached database manager singleton."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.init_db()
    return _db_manager
