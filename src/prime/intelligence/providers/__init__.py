"""Local LLM provider interfaces and Apple Silicon MLX backend."""

from prime.intelligence.providers.base import (
    DEFAULT_M1_PROFILES,
    ChatMessage,
    GenerationRequest,
    GenerationResponse,
    LLMProvider,
    ModelSpec,
    ProviderMemoryReport,
    ProviderNotConfiguredError,
    ProviderStatus,
    StreamChunk,
)
from prime.intelligence.providers.mlx_provider import MLXProvider

__all__ = [
    "DEFAULT_M1_PROFILES",
    "ChatMessage",
    "GenerationRequest",
    "GenerationResponse",
    "LLMProvider",
    "MLXProvider",
    "ModelSpec",
    "ProviderMemoryReport",
    "ProviderNotConfiguredError",
    "ProviderStatus",
    "StreamChunk",
]
