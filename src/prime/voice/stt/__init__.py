"""Offline Speech-to-Text registry and Whisper.cpp provider."""

from prime.voice.stt.registry import (
    APPROVED_STT_MODELS,
    ApprovedSTTModel,
    STTModelRegistry,
    STTModelSecurityError,
)
from prime.voice.stt.whisper_provider import WhisperCppSTTProvider

__all__ = [
    "APPROVED_STT_MODELS",
    "ApprovedSTTModel",
    "STTModelRegistry",
    "STTModelSecurityError",
    "WhisperCppSTTProvider",
]
