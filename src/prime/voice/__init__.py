"""Voice subsystem (offline STT, offline TTS, push-to-talk, opt-in double-clap)."""

from prime.voice.audio_capture import (
    AudioCaptureConfig,
    AudioCaptureSession,
    compute_rms,
    is_silent,
)
from prime.voice.contracts import (
    ActivationSnapshot,
    ActivationStatus,
    AudioPolicy,
    SpeechLanguage,
    STTProvider,
    STTResult,
    TTSProvider,
    VoicePipelineError,
)
from prime.voice.double_clap import DoubleClapConfig, DoubleClapDetector, DoubleClapMonitor
from prime.voice.permissions import check_microphone_permission, request_microphone_permission
from prime.voice.service import VoiceCoordinator, VoiceStatusSnapshot
from prime.voice.stt import (
    APPROVED_STT_MODELS,
    ApprovedSTTModel,
    STTModelRegistry,
    STTModelSecurityError,
    WhisperCppSTTProvider,
)
from prime.voice.tts import AVSpeechTTSProvider, LocalVoiceInfo, contains_bangla

__all__ = [
    "APPROVED_STT_MODELS",
    "AVSpeechTTSProvider",
    "ActivationSnapshot",
    "ActivationStatus",
    "ApprovedSTTModel",
    "AudioCaptureConfig",
    "AudioCaptureSession",
    "AudioPolicy",
    "DoubleClapConfig",
    "DoubleClapDetector",
    "DoubleClapMonitor",
    "LocalVoiceInfo",
    "STTModelRegistry",
    "STTModelSecurityError",
    "STTProvider",
    "STTResult",
    "SpeechLanguage",
    "TTSProvider",
    "VoiceCoordinator",
    "VoicePipelineError",
    "VoiceStatusSnapshot",
    "WhisperCppSTTProvider",
    "check_microphone_permission",
    "compute_rms",
    "contains_bangla",
    "is_silent",
    "request_microphone_permission",
]
