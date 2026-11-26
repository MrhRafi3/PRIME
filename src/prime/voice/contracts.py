"""Offline voice pipeline contracts for future Phase 03/04 implementation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class VoicePipelineError(RuntimeError):
    """Raised when an unconfigured or disallowed voice operation is invoked."""


class ActivationStatus(StrEnum):
    """Availability status for activation triggers."""

    CONFIGURED_UNAVAILABLE = "configured_unavailable"
    READY = "ready"
    DISABLED = "disabled"
    ACTIVE = "active"


@dataclass(frozen=True, slots=True)
class ActivationSnapshot:
    """UI-facing state for push-to-talk and double-clap configuration."""

    push_to_talk_pressed: bool
    push_to_talk_status: ActivationStatus
    double_clap_enabled: bool
    double_clap_status: ActivationStatus
    microphone_permission_requested: bool = False


class SpeechLanguage(StrEnum):
    BANGLA = "bn"
    ENGLISH = "en"
    AUTO_BN_EN = "bn-en"


@dataclass(frozen=True, slots=True)
class AudioPolicy:
    """Privacy policy ensuring no silent background recording or wake-word in Phase 02."""

    push_to_talk_enabled: bool = True
    double_clap_enabled: bool = True
    wake_word_enabled: bool = False
    background_recording_allowed: bool = False
    log_raw_audio: bool = False


@dataclass(frozen=True, slots=True)
class STTResult:
    text: str
    language: SpeechLanguage
    confidence: float = 0.0
    duration_ms: int = 0


class STTProvider(Protocol):
    """Offline Speech-to-Text contract (e.g., mlx-whisper / whisper.cpp)."""

    def transcribe_pcm(self, pcm_bytes: bytes, *, sample_rate: int = 16000) -> STTResult:
        """Transcribe bounded PCM audio locally."""


class TTSProvider(Protocol):
    """Offline Text-to-Speech contract (e.g., Kokoro / AVSpeechSynthesizer)."""

    def synthesize_to_pcm(self, text: str, *, language: SpeechLanguage) -> bytes:
        """Synthesize local speech audio without network calls."""
