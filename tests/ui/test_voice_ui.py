"""PySide6 / QML bridge and Phase 05 voice UI integration tests (hardware-safe)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from prime.config import LanguageMode, MemoryProfile, load_config
from prime.core import AssistantState, PrimeApp
from prime.security.tiers import PermissionState
from prime.ui.bridge import PrimeUIBridge
from prime.voice.audio_capture import AudioCaptureConfig, AudioCaptureSession
from prime.voice.contracts import SpeechLanguage, STTResult
from prime.voice.double_clap import DoubleClapMonitor
from prime.voice.service import VoiceCoordinator
from prime.voice.stt.registry import STTModelRegistry


def _get_qt_app() -> QGuiApplication:
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    app = QGuiApplication(["prime-voice-ui-test"])
    QQuickStyle.setStyle("Basic")
    return app


class _FakeStream:
    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def close(self) -> None:
        return None


class _MockSTTProvider:
    def __init__(self, transcript: str = "Local voice test") -> None:
        self._loaded = False
        self._transcript = transcript
        self._cancelled = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def active_model_id(self) -> str | None:
        return "whisper-small-q5_1" if self._loaded else None

    def load(self, _slug: str, _path: Path) -> None:
        self._loaded = True

    def unload(self) -> None:
        self._loaded = False

    def cancel(self) -> None:
        self._cancelled = True

    def transcribe_array(
        self,
        samples: np.ndarray,
        *,
        sample_rate: int = 16000,
        language: SpeechLanguage = SpeechLanguage.AUTO_BN_EN,
        cancel_event: Any = None,
    ) -> STTResult:
        _ = (samples, sample_rate, cancel_event)
        return STTResult(text=self._transcript, language=language, confidence=1.0, duration_ms=120)


class _MockTTSProvider:
    def __init__(self) -> None:
        self.speaking = False
        self.english_voice = "Daniel"
        self.bangla_voice = "Piya"
        self.rate = 0.5
        self.volume = 0.9
        self.spoken: list[str] = []

    @property
    def is_speaking(self) -> bool:
        return self.speaking

    def configure(
        self,
        *,
        english_voice: str | None = None,
        bangla_voice: str | None = None,
        rate: float | None = None,
        volume: float | None = None,
    ) -> None:
        if english_voice:
            self.english_voice = english_voice
        if bangla_voice:
            self.bangla_voice = bangla_voice
        if rate is not None:
            self.rate = rate
        if volume is not None:
            self.volume = volume

    def speak(self, text: str, **_kwargs) -> bool:
        self.speaking = True
        self.spoken.append(text)
        return True

    def stop(self) -> None:
        self.speaking = False

    def list_voices(self):
        return ()


@pytest.mark.ui
def test_phase05_qml_loads_with_zero_warnings_and_voice_defaults(tmp_path: Path) -> None:
    qt_app = _get_qt_app()
    cfg = load_config(
        env={
            "PRIME_DATA_DIR": str(tmp_path / "data"),
            "PRIME_LOG_DIR": str(tmp_path / "logs"),
            "PRIME_ENVIRONMENT": "test",
        }
    )
    app = PrimeApp(cfg, platform_override="darwin")
    app.voice = VoiceCoordinator(
        cfg.voice,
        app._stt_registry,
        double_clap_enabled=cfg.activation.double_clap_enabled,
        stt_provider=_MockSTTProvider(),  # type: ignore[arg-type]
        tts_provider=_MockTTSProvider(),  # type: ignore[arg-type]
        permission_checker=lambda: PermissionState.NOT_DETERMINED,
        capture_factory=lambda **kw: AudioCaptureSession(
            AudioCaptureConfig(),
            stream_factory=lambda **skw: _FakeStream(),
            on_level=kw.get("on_level"),
        ),
    )
    app.bootstrap()
    bridge = PrimeUIBridge(app, start_timers=False)

    engine = QQmlApplicationEngine()
    warnings: list[str] = []
    engine.warnings.connect(lambda errs: warnings.extend(e.toString() for e in errs))
    engine.rootContext().setContextProperty("primeBridge", bridge)

    qml_path = Path(__file__).resolve().parents[2] / "src" / "prime" / "ui" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    qt_app.processEvents()

    try:
        assert len(engine.rootObjects()) == 1
        assert warnings == []
        assert bridge.doubleClapEnabled is False
        assert bridge.doubleClapMonitoring is False
        assert bridge.doubleClapStatusText == "Disabled (Default)"
        assert bridge.micPermissionText == "Not Requested"
        assert bridge.sttModelSlug == "whisper-small-q5_1"
        assert bridge.ttsEnabled is True
        assert bridge.ttsEnglishVoice == "Daniel"
        assert bridge.pttShortcut == "Ctrl+Space"
    finally:
        for obj in engine.rootObjects():
            obj.close()
        qt_app.processEvents()
        del engine
        bridge.shutdown()
        app.shutdown()


@pytest.mark.ui
def test_ui_bridge_voice_ptt_cancel_double_clap_and_settings_persistence(tmp_path: Path) -> None:
    _get_qt_app()
    cfg_path = tmp_path / "data" / "config.toml"
    cfg = load_config(
        env={
            "PRIME_DATA_DIR": str(tmp_path / "data"),
            "PRIME_LOG_DIR": str(tmp_path / "logs"),
            "PRIME_ENVIRONMENT": "test",
        }
    )
    stt_dir = tmp_path / "stt"
    stt_dir.mkdir(parents=True)
    (stt_dir / "ggml-small-q5_1.bin").write_bytes(b"ggml" * 1024)

    mock_tts = _MockTTSProvider()
    mock_stt = _MockSTTProvider(transcript="Hello PRIME from microphone")

    app = PrimeApp(cfg, platform_override="darwin")
    app._stt_registry = STTModelRegistry(stt_dir)
    app.voice = VoiceCoordinator(
        cfg.voice,
        app._stt_registry,
        double_clap_enabled=False,
        stt_provider=mock_stt,  # type: ignore[arg-type]
        tts_provider=mock_tts,  # type: ignore[arg-type]
        permission_checker=lambda: PermissionState.GRANTED,
        capture_factory=lambda **kw: AudioCaptureSession(
            AudioCaptureConfig(),
            stream_factory=lambda **skw: _FakeStream(),
            on_level=kw.get("on_level"),
        ),
    )
    app.voice._clap_monitor = DoubleClapMonitor(stream_factory=lambda **kw: _FakeStream())
    app.bootstrap()
    bridge = PrimeUIBridge(app, start_timers=False)

    try:
        # 1. Start PTT and verify live waveform level + state transition
        bridge.startPushToTalk()
        assert bridge.isRecording is True
        assert bridge.assistantState == AssistantState.LISTENING.value
        app.voice._capture.push_test_samples(np.full(2048, 0.25, dtype=np.float32))
        assert bridge.micLevel > 0.0

        # 2. Release PTT triggers synchronous fallback transcription when threads aren't started
        bridge.releasePushToTalk()
        assert bridge.isRecording is False
        assert bridge.sttLoaded is True
        assert bridge.transcriptionPreview == "Hello PRIME from microphone"
        assert bridge.messagesModel.rowCount() == 2

        # 3. Cancel voice input wipes state cleanly
        bridge.startPushToTalk()
        bridge.cancelVoiceInput()
        assert bridge.isRecording is False
        assert bridge.micLevel == 0.0
        assert bridge.transcriptionPreview == "Voice input cancelled."

        # 4. Double-clap monitoring refuses when disabled, starts after opt-in
        bridge.toggleDoubleClapMonitoring()
        assert bridge.doubleClapMonitoring is False
        assert "disabled" in bridge.voiceErrorText.lower()

        bridge.saveAllPreferences(
            LanguageMode.BANGLA_ENGLISH.value,
            MemoryProfile.BALANCED.value,
            True,
            "qwen2.5-1.5b-4bit",
            "whisper-small-q5_1",
            False,
            "Samantha",
            0.7,
            0.8,
        )
        assert bridge.doubleClapEnabled is True
        assert bridge.ttsEnabled is False
        assert bridge.ttsEnglishVoice == "Samantha"

        bridge.toggleDoubleClapMonitoring()
        assert bridge.doubleClapMonitoring is True
        assert bridge.doubleClapStatusText == "MONITORING ACTIVE (Mic Live)"

        reloaded = load_config(config_path=cfg_path, env={})
        assert reloaded.activation.double_clap_enabled is True
        assert reloaded.voice.tts_enabled is False
        assert reloaded.voice.tts_english_voice == "Samantha"
        assert reloaded.voice.tts_rate == pytest.approx(0.7)
        assert reloaded.voice.tts_volume == pytest.approx(0.8)
    finally:
        bridge.shutdown()
        app.shutdown()
