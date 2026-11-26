"""Versioned SQLite database migrations for PRIME."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from prime.intelligence.memory.schema import BASE_TABLES_SQL, FTS5_SQL, supports_fts5


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    fn: Callable[[sqlite3.Connection], None]


def _migrate_v1_core_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(BASE_TABLES_SQL)


def _migrate_v2_memory_fts5(conn: sqlite3.Connection) -> None:
    if supports_fts5(conn):
        conn.executescript(FTS5_SQL)


MIGRATIONS: tuple[Migration, ...] = (
    Migration(version=1, name="core_tables", fn=_migrate_v1_core_tables),
    Migration(version=2, name="memory_fts5_index", fn=_migrate_v2_memory_fts5),
)

CURRENT_SCHEMA_VERSION = MIGRATIONS[-1].version


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version, or 0 if uninitialized."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if row is None:
        return 0
    ver_row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
    return int(ver_row[0]) if ver_row else 0


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Apply all pending migrations in order inside explicit transactions."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    current = get_schema_version(conn)
    for migration in MIGRATIONS:
        if migration.version <= current:
            continue
        now = datetime.now(tz=UTC).isoformat()
        with conn:
            migration.fn(conn)
            conn.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                (migration.version, migration.name, now),
            )
        current = migration.version
    return current
