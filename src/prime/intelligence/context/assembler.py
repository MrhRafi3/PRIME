"""Multi-turn prompt context builder grounded in SQLite MemoryStore and external prompt."""

from __future__ import annotations

from pathlib import Path

from prime.config.settings import LanguageMode
from prime.intelligence.memory.store import MemoryStore
from prime.intelligence.prompts.loader import load_system_prompt
from prime.intelligence.providers.base import ChatMessage


class ContextAssembler:
    """Assembles bounded system + history messages for local MLX inference."""

    def __init__(
        self,
        memory_store: MemoryStore,
        *,
        language_mode: LanguageMode = LanguageMode.BANGLA_ENGLISH,
        prompt_path: Path | None = None,
        max_history_messages: int = 10,
        max_chars_budget: int = 8000,
    ) -> None:
        self._memory = memory_store
        self._language_mode = language_mode
        self._prompt_path = prompt_path
        self._max_history_messages = max_history_messages
        self._max_chars_budget = max_chars_budget

    def build_messages(
        self,
        conversation_id: int,
        user_input: str,
        *,
        query_hint: str | None = None,
    ) -> tuple[ChatMessage, ...]:
        """Build bounded multi-turn messages including external system prompt and notes."""
        notes = self._memory.search_memory(query_hint or user_input, limit=5)
        formatted_notes = tuple(f"{n.key}: {n.content}" for n in notes)
        system_prompt = load_system_prompt(
            prompt_path=self._prompt_path,
            language_mode=self._language_mode,
            notes=formatted_notes,
        )

        history = self._memory.get_messages(conversation_id, limit=self._max_history_messages)
        selected: list[ChatMessage] = []
        used_chars = len(system_prompt) + len(user_input)

        # Keep most recent turns first within character budget for 8GB M1 context safety.
        for msg in reversed(history):
            if used_chars + len(msg.content) > self._max_chars_budget:
                break
            selected.append(ChatMessage(role=msg.role, content=msg.content))
            used_chars += len(msg.content)
        selected.reverse()

        return (
            ChatMessage(role="system", content=system_prompt),
            *selected,
            ChatMessage(role="user", content=user_input),
        )
