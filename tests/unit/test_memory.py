"""Unit tests for SQLite + FTS5 local memory, migrations, and ContextAssembler."""

from __future__ import annotations

import sqlite3
import stat
from pathlib import Path

import pytest

from prime.config import LanguageMode
from prime.intelligence.context import ContextAssembler
from prime.intelligence.memory import (
    CURRENT_SCHEMA_VERSION,
    MemoryPolicyError,
    MemorySensitivity,
    MemoryStore,
    apply_migrations,
    get_schema_version,
)


@pytest.mark.unit
def test_sqlite_initialization_permissions_and_migrations(tmp_path: Path) -> None:
    db_path = tmp_path / "secure_data" / "prime_memory.db"
    store = MemoryStore(db_path)
    version = store.initialize()
    try:
        assert version == CURRENT_SCHEMA_VERSION
        assert store.schema_version() == CURRENT_SCHEMA_VERSION
        assert stat.S_IMODE(db_path.parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(db_path.stat().st_mode) == 0o600
    finally:
        store.close()

    # Verify idempotent re-run of migrations
    conn = sqlite3.connect(db_path)
    try:
        assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION
        assert apply_migrations(conn) == CURRENT_SCHEMA_VERSION
    finally:
        conn.close()


@pytest.mark.unit
def test_memory_crud_fts5_and_sensitivity_policy(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "prime.db")
    store.initialize()
    try:
        with pytest.raises(MemoryPolicyError):
            store.upsert_memory(
                "personal",
                "national_id",
                "12345",
                sensitivity=MemorySensitivity.SENSITIVE,
                user_approved=False,
            )

        note = store.upsert_memory("notes", "meeting", "Project PRIME architecture review tomorrow")
        assert note.key == "meeting"

        updated = store.upsert_memory(
            "notes", "meeting", "Project PRIME architecture review Friday"
        )
        assert "Friday" in updated.content

        results = store.search_memory("architecture Friday")
        assert len(results) == 1
        assert results[0].key == "meeting"

        # SQL injection-like strings must be safely parameterized
        inj = store.search_memory("'; DROP TABLE memory_entries; --")
        assert inj == []
        assert store.get_memory("notes", "meeting") is not None

        assert store.delete_memory("notes", "meeting") is True
        assert store.get_memory("notes", "meeting") is None
    finally:
        store.close()


@pytest.mark.unit
def test_conversation_history_and_context_assembler(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "ctx.db")
    store.initialize()
    try:
        conv = store.create_conversation("Bangla + English Session")
        store.add_message(conv.id, "user", "Amar project status ki?", language="bn-en")
        store.add_message(conv.id, "assistant", "Phase 02 foundation ready.", language="en")
        store.upsert_memory("notes", "hardware", "MacBook Air M1 8GB RAM")

        assembler = ContextAssembler(store, language_mode=LanguageMode.BANGLA_ENGLISH)
        msgs = assembler.build_messages(conv.id, "Tell me about hardware", query_hint="hardware")
        assert msgs[0].role == "system"
        assert "MacBook Air M1 8GB RAM" in msgs[0].content
        assert any(m.content == "Amar project status ki?" for m in msgs)
        assert msgs[-1].role == "user"
        assert msgs[-1].content == "Tell me about hardware"
    finally:
        store.close()
