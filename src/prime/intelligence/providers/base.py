"""Provider-agnostic Local LLM contracts supporting streaming and cancellation."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from prime.config.settings import MemoryProfile


class ProviderNotConfiguredError(RuntimeError):
    """Raised when local inference is invoked without a loaded local model."""


class ProviderStatus(StrEnum):
    UNINITIALIZED = "uninitialized"
    READY = "ready"
    LOADING = "loading"
    LOADED = "loaded"
    GENERATING = "generating"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    model_id: str
    backend: str
    quantization: str
    estimated_ram_mb: int
    max_context_tokens: int
    supports_bangla: bool = True


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    messages: tuple[ChatMessage, ...]
    max_tokens: int = 512
    temperature: float = 0.4
    top_p: float = 0.9


@dataclass(frozen=True, slots=True)
class StreamChunk:
    text: str
    token_count: int
    tokens_per_sec: float = 0.0
    finish_reason: str | None = None
    peak_memory_gb: float = 0.0


@dataclass(frozen=True, slots=True)
class GenerationResponse:
    text: str
    model_id: str
    tokens_generated: int = 0
    tokens_per_sec: float = 0.0
    cancelled: bool = False
    finish_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderMemoryReport:
    backend: str
    active_memory_mb: float
    peak_memory_mb: float


DEFAULT_M1_PROFILES: dict[MemoryProfile, ModelSpec] = {
    MemoryProfile.ECO: ModelSpec(
        model_id="qwen2.5-1.5b-4bit",
        backend="mlx",
        quantization="4bit",
        estimated_ram_mb=1400,
        max_context_tokens=4096,
        supports_bangla=True,
    ),
    MemoryProfile.BALANCED: ModelSpec(
        model_id="qwen2.5-3b-4bit",
        backend="mlx",
        quantization="4bit",
        estimated_ram_mb=2450,
        max_context_tokens=4096,
        supports_bangla=True,
    ),
    MemoryProfile.HEAVY: ModelSpec(
        model_id="7b-4bit-local",
        backend="mlx",
        quantization="4bit",
        estimated_ram_mb=4900,
        max_context_tokens=2048,
        supports_bangla=True,
    ),
}


class LLMProvider(Protocol):
    """Contract for 100% local LLM backends (MLX-LM primary on Apple Silicon)."""

    @property
    def is_loaded(self) -> bool:
        """Whether a model is currently resident in memory."""

    @property
    def active_model_id(self) -> str | None:
        """Identifier of the currently loaded model, if any."""

    def initialize(self) -> None:
        """Verify backend readiness without loading any model weights."""

    def is_model_available(self, model_path: Path) -> bool:
        """Return True only if local model files exist on disk."""

    def load(self, spec: ModelSpec, *, model_path: Path | None = None) -> None:
        """Load the specified verified local model."""

    def unload(self) -> None:
        """Release model weights and reclaim memory."""

    def stream_generate(
        self,
        request: GenerationRequest,
        *,
        cancel_event: threading.Event | None = None,
    ) -> Iterator[StreamChunk]:
        """Yield streamed token deltas until completion or cancellation."""

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate a synchronous local completion."""

    def cancel(self) -> None:
        """Request immediate cancellation of any active generation."""

    def status(self) -> ProviderStatus:
        """Return current provider lifecycle status."""

    def memory_report(self) -> ProviderMemoryReport:
        """Return active and peak runtime memory usage."""
