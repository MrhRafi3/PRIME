"""Local LLM provider interfaces and M1 8GB model profile specs."""

from prime.intelligence.providers.base import (
    DEFAULT_M1_PROFILES,
    ChatMessage,
    GenerationRequest,
    GenerationResponse,
    LLMProvider,
    ModelSpec,
    ProviderNotConfiguredError,
)

__all__ = [
    "DEFAULT_M1_PROFILES",
    "ChatMessage",
    "GenerationRequest",
    "GenerationResponse",
    "LLMProvider",
    "ModelSpec",
    "ProviderNotConfiguredError",
]
