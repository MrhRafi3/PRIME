"""SQLite schema models and FTS5 capability detection for PRIME."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import StrEnum


class MemorySensitivity(StrEnum):
    PUBLIC = "public"
    NORMAL = "normal"
    SENSITIVE = "sensitive"


@dataclass(frozen=True, slots=True)
class ConversationRecord:
    id: int
    title: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class MessageRecord:
    id: int
    conversation_id: int
    role: str
    content: str
    language: str
    created_at: str


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    id: int
    category: str
    key: str
    content: str
    sensitivity: MemorySensitivity
    created_at: str
    updated_at: str


def supports_fts5(conn: sqlite3.Connection) -> bool:
    """Return True if this SQLite build supports FTS5 virtual tables."""
    try:
        rows = conn.execute("PRAGMA compile_options").fetchall()
    except sqlite3.Error:
        return False
    return any("ENABLE_FTS5" in str(row[0]) for row in rows)


BASE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('system', 'user', 'assistant')),
    content TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
    ON messages(conversation_id, id);

CREATE TABLE IF NOT EXISTS memory_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    entry_key TEXT NOT NULL,
    content TEXT NOT NULL,
    sensitivity TEXT NOT NULL DEFAULT 'normal'
        CHECK(sensitivity IN ('public', 'normal', 'sensitive')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(category, entry_key)
);

CREATE INDEX IF NOT EXISTS idx_memory_category
    ON memory_entries(category);
"""

FTS5_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    category,
    entry_key,
    content,
    content='memory_entries',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS memory_entries_ai AFTER INSERT ON memory_entries BEGIN
    INSERT INTO memory_fts(rowid, category, entry_key, content)
    VALUES (new.id, new.category, new.entry_key, new.content);
END;

CREATE TRIGGER IF NOT EXISTS memory_entries_ad AFTER DELETE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, category, entry_key, content)
    VALUES ('delete', old.id, old.category, old.entry_key, old.content);
END;

CREATE TRIGGER IF NOT EXISTS memory_entries_au AFTER UPDATE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, category, entry_key, content)
    VALUES ('delete', old.id, old.category, old.entry_key, old.content);
    INSERT INTO memory_fts(rowid, category, entry_key, content)
    VALUES (new.id, new.category, new.entry_key, new.content);
END;
"""
