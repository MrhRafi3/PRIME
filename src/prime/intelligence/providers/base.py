"""Provider-agnostic Local LLM contracts (no runtime inference imported in Phase 02)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from prime.config.settings import MemoryProfile


class ProviderNotConfiguredError(RuntimeError):
    """Raised when local inference is invoked before Phase 03 runtime integration."""


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


@dataclass(frozen=True, slots=True)
class GenerationResponse:
    text: str
    model_id: str
    tokens_generated: int = 0


DEFAULT_M1_PROFILES: dict[MemoryProfile, ModelSpec] = {
    MemoryProfile.ECO: ModelSpec(
        model_id="1.5b-4bit-local",
        backend="mlx",
        quantization="4bit",
        estimated_ram_mb=1300,
        max_context_tokens=2048,
        supports_bangla=True,
    ),
    MemoryProfile.BALANCED: ModelSpec(
        model_id="3b-4b-4bit-local",
        backend="mlx",
        quantization="4bit",
        estimated_ram_mb=2500,
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
    """Contract for local-only LLM backends (MLX / llama.cpp in Phase 03)."""

    @property
    def is_loaded(self) -> bool:
        """Whether a model is currently resident in memory."""

    def load(self, spec: ModelSpec) -> None:
        """Load the specified verified local model."""

    def unload(self) -> None:
        """Release model weights and reclaim unified memory."""

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate a synchronous local completion."""
