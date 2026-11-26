"""Cohesive local voice pipeline coordinator (PTT, STT, TTS, opt-in Double-Clap)."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass

from prime.config.settings import LanguageMode, VoiceConfig
from prime.logging.logger import get_logger, log_event
from prime.security.policy import PermissionDeniedError
from prime.security.tiers import PermissionState
from prime.voice.audio_capture import AudioCaptureConfig, AudioCaptureSession
from prime.voice.contracts import (
    ActivationSnapshot,
    ActivationStatus,
    SpeechLanguage,
    STTResult,
    VoicePipelineError,
)
from prime.voice.double_clap import DoubleClapConfig, DoubleClapMonitor
from prime.voice.permissions import check_microphone_permission, request_microphone_permission
from prime.voice.stt.registry import STTModelRegistry
from prime.voice.stt.whisper_provider import WhisperCppSTTProvider
from prime.voice.tts.avspeech_provider import AVSpeechTTSProvider, LocalVoiceInfo


@dataclass(frozen=True, slots=True)
class VoiceStatusSnapshot:
    mic_permission: PermissionState
    recording: bool
    transcribing: bool
    speaking: bool
    double_clap_enabled: bool
    double_clap_monitoring: bool
    stt_loaded: bool
    stt_model_slug: str
    stt_model_available: bool
    tts_enabled: bool
    tts_english_voice: str
    tts_bangla_voice: str
    tts_rate: float
    tts_volume: float


class VoiceCoordinator:
    """Coordinates local-only audio capture, Whisper STT, AVSpeech TTS, and Double-Clap."""

    def __init__(
        self,
        voice_config: VoiceConfig,
        stt_registry: STTModelRegistry,
        *,
        double_clap_enabled: bool = False,
        clap_threshold: int = 2000,
        clap_min_interval_s: float = 0.1,
        clap_max_interval_s: float = 0.8,
        stt_provider: WhisperCppSTTProvider | None = None,
        tts_provider: AVSpeechTTSProvider | None = None,
        permission_checker: Callable[[], PermissionState] | None = None,
        permission_requester: Callable[[], PermissionState] | None = None,
        capture_factory: Callable[..., AudioCaptureSession] | None = None,
        on_level: Callable[[float, float], None] | None = None,
        on_double_clap: Callable[[], None] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._config = voice_config
        self._stt_registry = stt_registry
        self._stt = stt_provider or WhisperCppSTTProvider()
        self._tts = tts_provider or AVSpeechTTSProvider(
            english_voice=voice_config.tts_english_voice,
            bangla_voice=voice_config.tts_bangla_voice,
            rate=voice_config.tts_rate,
            volume=voice_config.tts_volume,
        )
        self._double_clap_enabled = bool(double_clap_enabled)
        self._perm_check = permission_checker or check_microphone_permission
        self._perm_request = permission_requester or request_microphone_permission
        self._on_level = on_level
        self._on_double_clap = on_double_clap
        self._logger = logger or get_logger("prime.voice")

        if capture_factory is not None:
            self._capture = capture_factory(on_level=self._handle_level)
        else:
            self._capture = AudioCaptureSession(
                AudioCaptureConfig(),
                on_level=self._handle_level,
            )

        self._clap_monitor = DoubleClapMonitor(
            DoubleClapConfig(
                rms_threshold=max(0.01, min(0.5, clap_threshold / 32768.0)),
                min_interval_s=clap_min_interval_s,
                max_interval_s=clap_max_interval_s,
            ),
            on_detected=self._handle_double_clap,
        )
        self._transcribing = False
        self._mic_requested_explicitly = False

    @property
    def stt_provider(self) -> WhisperCppSTTProvider:
        return self._stt

    @property
    def tts_provider(self) -> AVSpeechTTSProvider:
        return self._tts

    def _handle_level(self, level: float, elapsed_s: float) -> None:
        if self._on_level is not None:
            self._on_level(level, elapsed_s)

    def _handle_double_clap(self) -> None:
        log_event(
            self._logger,
            logging.INFO,
            "voice.double_clap_detected",
            "Opt-in double-clap trigger confirmed locally",
        )
        if self._on_double_clap is not None:
            self._on_double_clap()

    def set_level_callback(self, callback: Callable[[float, float], None] | None) -> None:
        self._on_level = callback

    def set_double_clap_callback(self, callback: Callable[[], None] | None) -> None:
        self._on_double_clap = callback

    def update_config(self, config: VoiceConfig, *, double_clap_enabled: bool) -> None:
        self._config = config
        self._double_clap_enabled = bool(double_clap_enabled)
        self._tts.configure(
            english_voice=config.tts_english_voice,
            bangla_voice=config.tts_bangla_voice,
            rate=config.tts_rate,
            volume=config.tts_volume,
        )
        if not self._double_clap_enabled and self._clap_monitor.is_monitoring:
            self._clap_monitor.stop()

    def check_mic_permission(self) -> PermissionState:
        """Non-prompting check of macOS microphone TCC status."""
        return self._perm_check()

    def request_mic_permission(self) -> PermissionState:
        """Explicit user-initiated microphone permission request."""
        self._mic_requested_explicitly = True
        return self._perm_request()

    def _ensure_mic_permission(self, *, allow_prompt: bool = True) -> PermissionState:
        state = self._perm_check()
        if state == PermissionState.NOT_DETERMINED and allow_prompt:
            state = self.request_mic_permission()
        if state != PermissionState.GRANTED:
            raise PermissionDeniedError(
                f"Microphone permission is {state.value}. "
                "Enable Microphone access in macOS System Settings -> Privacy & Security."
            )
        return state

    def status(self) -> VoiceStatusSnapshot:
        slug = self._config.stt_model_slug
        return VoiceStatusSnapshot(
            mic_permission=self._perm_check(),
            recording=self._capture.is_active,
            transcribing=self._transcribing,
            speaking=self._tts.is_speaking,
            double_clap_enabled=self._double_clap_enabled,
            double_clap_monitoring=self._clap_monitor.is_monitoring,
            stt_loaded=self._stt.is_loaded,
            stt_model_slug=slug,
            stt_model_available=self._stt_registry.is_installed(slug),
            tts_enabled=self._config.tts_enabled,
            tts_english_voice=self._tts.english_voice,
            tts_bangla_voice=self._tts.bangla_voice,
            tts_rate=self._tts.rate,
            tts_volume=self._tts.volume,
        )

    def activation_snapshot(self, *, ptt_enabled: bool, ptt_pressed: bool) -> ActivationSnapshot:
        ptt_status = (
            ActivationStatus.ACTIVE
            if ptt_pressed
            else (ActivationStatus.READY if ptt_enabled else ActivationStatus.DISABLED)
        )
        clap_status = (
            ActivationStatus.ACTIVE
            if self._clap_monitor.is_monitoring
            else (
                ActivationStatus.READY if self._double_clap_enabled else ActivationStatus.DISABLED
            )
        )
        return ActivationSnapshot(
            push_to_talk_pressed=ptt_pressed,
            push_to_talk_status=ptt_status,
            double_clap_enabled=self._double_clap_enabled,
            double_clap_status=clap_status,
            microphone_permission_requested=self._mic_requested_explicitly,
        )

    def load_stt(self, slug: str | None = None) -> None:
        target_slug = slug or self._config.stt_model_slug
        if not self._stt_registry.is_installed(target_slug):
            raise FileNotFoundError(
                f"STT model '{target_slug}' is not installed under {self._stt_registry.stt_dir}."
            )
        model_path = self._stt_registry.resolve_model_path(target_slug)
        self._stt.load(target_slug, model_path)
        log_event(
            self._logger,
            logging.INFO,
            "voice.stt_loaded",
            "Offline Whisper STT model loaded",
            context={"stt_model": target_slug},
        )

    def unload_stt(self) -> None:
        self._stt.unload()
        log_event(self._logger, logging.INFO, "voice.stt_unloaded", "Offline STT model unloaded")

    def start_recording(self, *, allow_prompt: bool = True) -> None:
        self._ensure_mic_permission(allow_prompt=allow_prompt)
        # Barge-in: stop TTS if currently speaking before capturing user speech
        if self._tts.is_speaking:
            self._tts.stop()
        # Pause double-clap stream if active to avoid dual CoreAudio contention
        if self._clap_monitor.is_monitoring:
            self._clap_monitor.stop()
        self._capture.start()
        log_event(self._logger, logging.INFO, "voice.recording_started", "Push-to-talk capture on")

    def stop_and_transcribe(
        self,
        *,
        language_mode: LanguageMode = LanguageMode.BANGLA_ENGLISH,
    ) -> STTResult:
        samples = self._capture.stop_and_consume()
        try:
            if samples.size == 0:
                return STTResult(text="", language=SpeechLanguage.AUTO_BN_EN)

            if not self._stt.is_loaded:
                self.load_stt()

            self._transcribing = True
            speech_lang = (
                SpeechLanguage.AUTO_BN_EN
                if language_mode == LanguageMode.BANGLA_ENGLISH
                else SpeechLanguage.ENGLISH
            )
            result = self._stt.transcribe_array(samples, sample_rate=16000, language=speech_lang)
            return result
        finally:
            self._transcribing = False
            if samples.size > 0:
                samples.fill(0.0)
            if self._double_clap_enabled and self._perm_check() == PermissionState.GRANTED:
                with contextlib.suppress(VoicePipelineError):
                    self._clap_monitor.start()

    def cancel_voice_input(self) -> None:
        self._capture.cancel()
        self._stt.cancel()
        self._transcribing = False
        log_event(self._logger, logging.INFO, "voice.cancelled", "Voice capture/STT cancelled")

    def set_double_clap_monitoring(self, enabled: bool, *, allow_prompt: bool = True) -> bool:
        if not enabled:
            self._clap_monitor.stop()
            return False
        if not self._double_clap_enabled:
            raise VoicePipelineError(
                "Double-clap activation is disabled. Opt in via Settings before monitoring."
            )
        self._ensure_mic_permission(allow_prompt=allow_prompt)
        self._clap_monitor.start()
        log_event(
            self._logger,
            logging.INFO,
            "voice.double_clap_monitoring_started",
            "Opt-in double-clap transient monitoring active",
        )
        return True

    def speak(
        self,
        text: str,
        *,
        language_mode: LanguageMode = LanguageMode.BANGLA_ENGLISH,
        on_finished: Callable[[], None] | None = None,
    ) -> bool:
        if not self._config.tts_enabled:
            if on_finished is not None:
                on_finished()
            return False
        speech_lang = (
            SpeechLanguage.AUTO_BN_EN
            if language_mode == LanguageMode.BANGLA_ENGLISH
            else SpeechLanguage.ENGLISH
        )
        return self._tts.speak(text, language=speech_lang, on_finished=on_finished)

    def stop_speaking(self) -> None:
        self._tts.stop()

    def list_available_voices(self) -> tuple[LocalVoiceInfo, ...]:
        return self._tts.list_voices()

    def shutdown(self) -> None:
        self._tts.stop()
        self._clap_monitor.stop()
        self._capture.cancel()
        self._stt.unload()
