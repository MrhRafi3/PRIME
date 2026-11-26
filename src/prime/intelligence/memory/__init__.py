"""Local SQLite + FTS5 persistent memory foundation."""

from prime.intelligence.memory.migrations import (
    CURRENT_SCHEMA_VERSION,
    apply_migrations,
    get_schema_version,
)
from prime.intelligence.memory.schema import (
    ConversationRecord,
    MemoryEntry,
    MemorySensitivity,
    MessageRecord,
    supports_fts5,
)
from prime.intelligence.memory.store import MemoryPolicyError, MemoryStore

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "ConversationRecord",
    "MemoryEntry",
    "MemoryPolicyError",
    "MemorySensitivity",
    "MemoryStore",
    "MessageRecord",
    "apply_migrations",
    "get_schema_version",
    "supports_fts5",
]
