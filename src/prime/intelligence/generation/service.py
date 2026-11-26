"""Local text generation orchestration with memory-budget and token-limit enforcement."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass

from prime.intelligence.providers.base import (
    ChatMessage,
    GenerationRequest,
    GenerationResponse,
    LLMProvider,
    ModelSpec,
    StreamChunk,
)


class MemoryBudgetError(MemoryError):
    """Raised when a model's estimated footprint exceeds the configured M1 RAM budget."""


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    memory_budget_mb: int = 3200
    max_context_tokens: int = 4096
    max_generation_tokens: int = 512
    temperature: float = 0.4
    top_p: float = 0.9


class GenerationService:
    """Enforces M1 8GB resource limits around LLMProvider calls."""

    def __init__(self, provider: LLMProvider, config: GenerationConfig) -> None:
        self._provider = provider
        self._config = config
        self._cancel_event = threading.Event()

    @property
    def config(self) -> GenerationConfig:
        return self._config

    def update_config(self, config: GenerationConfig) -> None:
        self._config = config

    def check_memory_budget(self, spec: ModelSpec) -> None:
        if spec.estimated_ram_mb > self._config.memory_budget_mb:
            raise MemoryBudgetError(
                f"Model '{spec.model_id}' requires ~{spec.estimated_ram_mb} MB RAM, "
                f"exceeding the configured M1 budget of {self._config.memory_budget_mb} MB."
            )

    def cancel(self) -> None:
        self._cancel_event.set()
        self._provider.cancel()

    def stream(
        self,
        messages: tuple[ChatMessage, ...],
        *,
        on_chunk: Callable[[StreamChunk], None] | None = None,
        max_tokens: int | None = None,
    ) -> GenerationResponse:
        self._cancel_event.clear()
        bounded_tokens = min(
            max_tokens or self._config.max_generation_tokens,
            self._config.max_generation_tokens,
        )
        request = GenerationRequest(
            messages=messages,
            max_tokens=max(1, bounded_tokens),
            temperature=self._config.temperature,
            top_p=self._config.top_p,
        )

        collected: list[str] = []
        token_count = 0
        tps = 0.0
        finish: str | None = None
        cancelled = False

        for chunk in self._provider.stream_generate(request, cancel_event=self._cancel_event):
            if chunk.text:
                collected.append(chunk.text)
            token_count = chunk.token_count
            tps = chunk.tokens_per_sec
            finish = chunk.finish_reason
            if on_chunk is not None:
                on_chunk(chunk)
            if finish == "cancelled" or self._cancel_event.is_set():
                cancelled = True
                break

        return GenerationResponse(
            text="".join(collected).strip(),
            model_id=self._provider.active_model_id or "",
            tokens_generated=token_count,
            tokens_per_sec=tps,
            cancelled=cancelled,
            finish_reason=finish or ("cancelled" if cancelled else "stop"),
        )
