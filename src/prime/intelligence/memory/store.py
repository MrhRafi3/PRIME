"""Parameterized SQLite + FTS5 local memory store with safe permissions."""

from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from prime.intelligence.memory.migrations import apply_migrations, get_schema_version
from prime.intelligence.memory.schema import (
    ConversationRecord,
    MemoryEntry,
    MemorySensitivity,
    MessageRecord,
    supports_fts5,
)

_VALID_ROLES = frozenset({"system", "user", "assistant"})


class MemoryPolicyError(ValueError):
    """Raised when an operation violates PRIME's memory privacy or validation policy."""


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _sanitize_fts_query(query: str) -> str:
    tokens = [tok.strip('"*():^') for tok in query.strip().split() if tok.strip('"*():^')]
    return " ".join(f'"{tok}"' for tok in tokens)


class MemoryStore:
    """Local ACID memory store backed by SQLite and optional FTS5 search."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._fts5_enabled = False

    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def fts5_enabled(self) -> bool:
        return self._fts5_enabled

    def initialize(self) -> int:
        """Create secure directory/DB file, apply migrations, and return schema version."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self._db_path.parent, 0o700)

        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")

        version = apply_migrations(conn)
        os.chmod(self._db_path, 0o600)

        self._conn = conn
        self._fts5_enabled = supports_fts5(conn)
        return version

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _require_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("MemoryStore has not been initialized.")
        return self._conn

    def schema_version(self) -> int:
        return get_schema_version(self._require_conn())

    def create_conversation(self, title: str = "New Session") -> ConversationRecord:
        clean_title = title.strip() or "New Session"
        now = _utc_now()
        conn = self._require_conn()
        with conn:
            cursor = conn.execute(
                "INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)",
                (clean_title, now, now),
            )
            conv_id = int(cursor.lastrowid)
        return ConversationRecord(id=conv_id, title=clean_title, created_at=now, updated_at=now)

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        *,
        language: str = "en",
    ) -> MessageRecord:
        if role not in _VALID_ROLES:
            raise MemoryPolicyError(f"Invalid message role: {role!r}")
        if not isinstance(content, str) or not content.strip():
            raise MemoryPolicyError("Message content cannot be empty.")
        now = _utc_now()
        conn = self._require_conn()
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, language, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, language, now),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
            msg_id = int(cursor.lastrowid)
        return MessageRecord(
            id=msg_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            language=language,
            created_at=now,
        )

    def get_messages(self, conversation_id: int, *, limit: int = 20) -> list[MessageRecord]:
        if limit < 1:
            raise MemoryPolicyError("limit must be >= 1")
        conn = self._require_conn()
        rows = conn.execute(
            """
            SELECT id, conversation_id, role, content, language, created_at
            FROM (
                SELECT id, conversation_id, role, content, language, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
            """,
            (conversation_id, limit),
        ).fetchall()
        return [
            MessageRecord(
                id=int(r["id"]),
                conversation_id=int(r["conversation_id"]),
                role=str(r["role"]),
                content=str(r["content"]),
                language=str(r["language"]),
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]

    def upsert_memory(
        self,
        category: str,
        key: str,
        content: str,
        *,
        sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
        user_approved: bool = False,
    ) -> MemoryEntry:
        clean_cat = category.strip()
        clean_key = key.strip()
        clean_content = content.strip()
        if not clean_cat or not clean_key or not clean_content:
            raise MemoryPolicyError("category, key, and content must be non-empty.")
        if sensitivity == MemorySensitivity.SENSITIVE and not user_approved:
            raise MemoryPolicyError(
                "Sensitive personal information requires explicit user approval before storage."
            )

        now = _utc_now()
        conn = self._require_conn()
        with conn:
            conn.execute(
                """
                INSERT INTO memory_entries (
                    category, entry_key, content, sensitivity, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(category, entry_key) DO UPDATE SET
                    content = excluded.content,
                    sensitivity = excluded.sensitivity,
                    updated_at = excluded.updated_at
                """,
                (clean_cat, clean_key, clean_content, sensitivity.value, now, now),
            )
        entry = self.get_memory(clean_cat, clean_key)
        assert entry is not None
        return entry

    def get_memory(self, category: str, key: str) -> MemoryEntry | None:
        conn = self._require_conn()
        row = conn.execute(
            """
            SELECT id, category, entry_key, content, sensitivity, created_at, updated_at
            FROM memory_entries
            WHERE category = ? AND entry_key = ?
            """,
            (category.strip(), key.strip()),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_entry(row)

    def search_memory(self, query: str, *, limit: int = 10) -> list[MemoryEntry]:
        if limit < 1:
            raise MemoryPolicyError("limit must be >= 1")
        cleaned = query.strip()
        if not cleaned:
            return []

        conn = self._require_conn()
        if self._fts5_enabled:
            fts_query = _sanitize_fts_query(cleaned)
            if fts_query:
                rows = conn.execute(
                    """
                    SELECT
                        m.id, m.category, m.entry_key, m.content,
                        m.sensitivity, m.created_at, m.updated_at
                    FROM memory_fts f
                    JOIN memory_entries m ON m.id = f.rowid
                    WHERE memory_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (fts_query, limit),
                ).fetchall()
                return [self._row_to_entry(r) for r in rows]

        like_pattern = f"%{cleaned}%"
        rows = conn.execute(
            """
            SELECT id, category, entry_key, content, sensitivity, created_at, updated_at
            FROM memory_entries
            WHERE category LIKE ? OR entry_key LIKE ? OR content LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (like_pattern, like_pattern, like_pattern, limit),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def delete_memory(self, category: str, key: str) -> bool:
        conn = self._require_conn()
        with conn:
            cursor = conn.execute(
                "DELETE FROM memory_entries WHERE category = ? AND entry_key = ?",
                (category.strip(), key.strip()),
            )
        return cursor.rowcount > 0

    def clear_all(self) -> None:
        conn = self._require_conn()
        with conn:
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM conversations")
            conn.execute("DELETE FROM memory_entries")

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(
            id=int(row["id"]),
            category=str(row["category"]),
            key=str(row["entry_key"]),
            content=str(row["content"]),
            sensitivity=MemorySensitivity(str(row["sensitivity"])),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
