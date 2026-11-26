"""Comprehensive offline unit and integration tests for PRIME Phase 05 voice pipeline."""

from __future__ import annotations

import hashlib
import socket
import sys
import threading
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from prime.config import load_config
from prime.core import AssistantState, PrimeApp
from prime.intelligence.providers import (
    GenerationRequest,
    GenerationResponse,
    ModelSpec,
    ProviderMemoryReport,
    ProviderStatus,
    StreamChunk,
)
from prime.intelligence.runtime import RuntimeState
from prime.security.policy import PermissionDeniedError
from prime.security.tiers import PermissionState
from prime.voice.audio_capture import (
    AudioCaptureConfig,
    AudioCaptureSession,
    compute_rms,
    is_silent,
)
from prime.voice.contracts import SpeechLanguage, VoicePipelineError
from prime.voice.double_clap import DoubleClapConfig, DoubleClapDetector, DoubleClapMonitor
from prime.voice.service import VoiceCoordinator
from prime.voice.stt.registry import ApprovedSTTModel, STTModelRegistry, STTModelSecurityError
from prime.voice.stt.whisper_provider import WhisperCppSTTProvider
from prime.voice.tts.avspeech_provider import AVSpeechTTSProvider, contains_bangla


class _FakeStream:
    """Deterministic fake sounddevice.InputStream for hardware-free unit tests."""

    def __init__(self, *, callback=None, fail_start: bool = False, **_kwargs) -> None:
        self.callback = callback
        self.fail_start = fail_start
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self) -> None:
        if self.fail_start:
            raise RuntimeError("fake audio device failure")
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


class _FakeLLM:
    def __init__(self, reply: str = "Local PRIME answer.") -> None:
        self._loaded = True
        self._reply = reply
        self.last_request: GenerationRequest | None = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def active_model_id(self) -> str | None:
        return "qwen2.5-1.5b-4bit" if self._loaded else None

    def initialize(self) -> None:
        return None

    def is_model_available(self, model_path: Path) -> bool:
        _ = model_path
        return True

    def status(self) -> ProviderStatus:
        return ProviderStatus.READY if self._loaded else ProviderStatus.UNINITIALIZED

    def load(self, model_spec: ModelSpec, *, model_path: Path | None = None) -> None:
        _ = (model_spec, model_path)
        self._loaded = True

    def unload(self) -> None:
        self._loaded = False

    def cancel(self) -> None:
        return None

    def memory_report(self) -> ProviderMemoryReport:
        return ProviderMemoryReport(
            backend="mlx",
            active_memory_mb=950.0,
            peak_memory_mb=1050.0,
        )

    def stream_generate(
        self,
        request: GenerationRequest,
        *,
        cancel_event: threading.Event | None = None,
    ):
        _ = cancel_event
        self.last_request = request
        yield StreamChunk(text=self._reply, token_count=4)
        return GenerationResponse(
            text=self._reply,
            model_id="qwen2.5-1.5b-4bit",
            tokens_generated=4,
            tokens_per_sec=20.0,
        )


def _install_fake_pywhispercpp(
    monkeypatch: pytest.MonkeyPatch,
    *,
    transcript: str = "হ্যালো প্রাইম",
    check_abort: bool = False,
) -> dict[str, Any]:
    calls: dict[str, Any] = {"instances": [], "transcribe_kwargs": []}

    class _FakeWhisperModel:
        def __init__(self, **kwargs) -> None:
            calls["instances"].append(kwargs)

        def transcribe(self, arr: np.ndarray, **kwargs):
            calls["transcribe_kwargs"].append((arr.copy(), kwargs))
            abort_cb = kwargs.get("abort_callback")
            if check_abort and callable(abort_cb) and abort_cb():
                raise RuntimeError("aborted")
            return [SimpleNamespace(text=transcript)]

    pkg = types.ModuleType("pywhispercpp")
    mod = types.ModuleType("pywhispercpp.model")
    mod.Model = _FakeWhisperModel  # type: ignore[attr-defined]
    pkg.model = mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pywhispercpp", pkg)
    monkeypatch.setitem(sys.modules, "pywhispercpp.model", mod)
    return calls


def _install_fake_avfaudio(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"spoken": [], "stopped_at": [], "rate": None, "volume": None}

    class _FakeVoice:
        def __init__(self, name: str, identifier: str, lang: str) -> None:
            self._name = name
            self._identifier = identifier
            self._lang = lang

        def name(self) -> str:
            return self._name

        def identifier(self) -> str:
            return self._identifier

        def language(self) -> str:
            return self._lang

    voices = [
        _FakeVoice("Daniel", "com.apple.voice.compact.en-GB.Daniel", "en-GB"),
        _FakeVoice("Piya", "com.apple.voice.compact.bn-IN.Paya", "bn-IN"),
    ]

    class _FakeAVSpeechSynthesisVoice:
        @staticmethod
        def speechVoices():
            return voices

        @staticmethod
        def voiceWithLanguage_(lang: str):
            for v in voices:
                if v.language() == lang:
                    return v
            return voices[0]

    class _FakeUtterance:
        def __init__(self, text: str) -> None:
            self.text = text
            self.voice = None

        @classmethod
        def speechUtteranceWithString_(cls, text: str):
            return cls(text)

        def setVoice_(self, voice) -> None:
            self.voice = voice

        def setRate_(self, rate: float) -> None:
            state["rate"] = rate

        def setVolume_(self, volume: float) -> None:
            state["volume"] = volume

    class _FakeSynthInstance:
        def __init__(self) -> None:
            self._speaking = False

        def isSpeaking(self) -> bool:
            return self._speaking

        def speakUtterance_(self, utterance: _FakeUtterance) -> None:
            self._speaking = True
            state["spoken"].append(
                (utterance.text, utterance.voice.name() if utterance.voice else None)
            )
            self._speaking = False

        def stopSpeakingAtBoundary_(self, boundary: int) -> None:
            state["stopped_at"].append(boundary)
            self._speaking = False

    class _FakeAVSpeechSynthesizer:
        @staticmethod
        def alloc():
            class _Alloc:
                @staticmethod
                def init():
                    return _FakeSynthInstance()

            return _Alloc()

    mod = types.ModuleType("AVFAudio")
    mod.AVSpeechSynthesisVoice = _FakeAVSpeechSynthesisVoice  # type: ignore[attr-defined]
    mod.AVSpeechUtterance = _FakeUtterance  # type: ignore[attr-defined]
    mod.AVSpeechSynthesizer = _FakeAVSpeechSynthesizer  # type: ignore[attr-defined]
    mod.AVSpeechUtteranceMinimumSpeechRate = 0.0  # type: ignore[attr-defined]
    mod.AVSpeechUtteranceMaximumSpeechRate = 1.0  # type: ignore[attr-defined]
    mod.AVSpeechBoundaryImmediate = 0  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "AVFAudio", mod)
    return state


@pytest.mark.unit
def test_stt_registry_approval_checksum_and_path_traversal(tmp_path: Path) -> None:
    payload = b"whisper-ggml-test-payload" * 100
    digest = hashlib.sha256(payload).hexdigest()
    catalog = {
        "valid-small": ApprovedSTTModel(
            slug="valid-small",
            display_name="Valid Small",
            filename="ggml-valid-small.bin",
            repo_id="ggerganov/whisper.cpp",
            size_mb=0.01,
            estimated_ram_mb=100,
            sha256=digest,
        ),
        "bad-path": ApprovedSTTModel(
            slug="bad-path",
            display_name="Bad Path",
            filename="../escape.bin",
            repo_id="local/test",
            size_mb=0.01,
            estimated_ram_mb=100,
            sha256=digest,
        ),
    }

    stt_dir = tmp_path / "stt"
    stt_dir.mkdir(parents=True)
    reg = STTModelRegistry(stt_dir, catalog=catalog)

    assert reg.is_installed("valid-small") is False
    assert reg.verify_checksum("valid-small") is False

    weight = stt_dir / "ggml-valid-small.bin"
    weight.write_bytes(payload)
    assert reg.is_installed("valid-small") is True
    assert reg.verify_checksum("valid-small") is True
    assert reg.list_installed()[0].slug == "valid-small"

    weight.write_bytes(b"corrupted" * 300)
    assert reg.verify_checksum("valid-small") is False

    with pytest.raises(STTModelSecurityError):
        reg.get_spec("unapproved-whisper")
    with pytest.raises(STTModelSecurityError):
        reg.resolve_model_path("bad-path")


@pytest.mark.unit
def test_whisper_provider_in_memory_transcription_cancel_and_no_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_pywhispercpp(
        monkeypatch, transcript="Amar sonar Bangla, PRIME status?", check_abort=True
    )

    def _deny_network(*_args, **_kwargs):
        raise AssertionError("Offline STT must never open network sockets")

    monkeypatch.setattr(socket, "create_connection", _deny_network)

    provider = WhisperCppSTTProvider(n_threads=4)
    assert provider.is_loaded is False

    with pytest.raises(VoicePipelineError):
        provider.transcribe_array(np.ones(1600, dtype=np.float32))

    fake_bin = tmp_path / "ggml-small-q5_1.bin"
    fake_bin.write_bytes(b"ggml" * 1024)
    provider.load("whisper-small-q5_1", fake_bin)
    assert provider.is_loaded is True
    assert provider.active_model_id == "whisper-small-q5_1"

    # Silence returns empty without invoking Whisper
    silent = np.zeros(8000, dtype=np.float32)
    res_silent = provider.transcribe_array(silent)
    assert res_silent.text == ""
    assert len(calls["transcribe_kwargs"]) == 0

    # Non-silent PCM array transcribes strictly in memory
    tone = (np.sin(np.linspace(0, 200, 16000)) * 0.25).astype(np.float32)
    res = provider.transcribe_array(tone, language=SpeechLanguage.AUTO_BN_EN)
    assert res.text == "Amar sonar Bangla, PRIME status?"
    assert len(calls["transcribe_kwargs"]) == 1
    assert calls["transcribe_kwargs"][0][1]["language"] == "auto"

    # PCM int16 bridge works too
    pcm_bytes = (tone * 32767.0).astype(np.int16).tobytes()
    res_pcm = provider.transcribe_pcm(pcm_bytes)
    assert res_pcm.text == "Amar sonar Bangla, PRIME status?"

    # Cancellation via external Event
    cancel_evt = threading.Event()
    cancel_evt.set()
    res_cancel = provider.transcribe_array(tone, cancel_event=cancel_evt)
    assert res_cancel.text == ""

    # Unload frees reference
    provider.unload()
    assert provider.is_loaded is False
    assert provider.active_model_id is None


@pytest.mark.unit
def test_avspeech_tts_bangla_english_selection_and_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _install_fake_avfaudio(monkeypatch)
    tts = AVSpeechTTSProvider(english_voice="Daniel", bangla_voice="Piya", rate=0.6, volume=0.85)

    assert contains_bangla("আমি ভালো আছি") is True
    assert contains_bangla("Ami bhalo achi") is False

    voices = tts.list_voices()
    assert {v.name for v in voices} == {"Daniel", "Piya"}

    finished = threading.Event()
    assert tts.speak("Hello Rafi", blocking=True, on_finished=finished.set) is True
    assert finished.is_set()
    assert state["spoken"][-1] == ("Hello Rafi", "Daniel")
    assert state["rate"] == pytest.approx(0.6)
    assert state["volume"] == pytest.approx(0.85)

    assert tts.speak("সুপ্রভাত রাফি", language=SpeechLanguage.AUTO_BN_EN, blocking=True) is True
    assert state["spoken"][-1] == ("সুপ্রভাত রাফি", "Piya")

    tts.stop()
    assert tts.is_speaking is False


@pytest.mark.unit
def test_audio_capture_in_memory_and_zero_wipe(tmp_path: Path) -> None:
    created_streams: list[_FakeStream] = []
    levels: list[float] = []

    def _factory(**kwargs):
        stream = _FakeStream(**kwargs)
        created_streams.append(stream)
        return stream

    session = AudioCaptureSession(
        AudioCaptureConfig(max_duration_s=2.0),
        stream_factory=_factory,
        on_level=lambda lvl, _t: levels.append(lvl),
    )
    session.start()
    assert session.is_active is True
    assert created_streams[0].started is True

    sample = np.full(1024, 0.2, dtype=np.float32)
    session.push_test_samples(sample)
    assert levels and levels[-1] > 0.5
    assert is_silent(sample) is False
    assert compute_rms(np.zeros(64, dtype=np.float32)) == 0.0

    captured = session.stop_and_consume()
    assert captured.size == 1024
    assert session.is_active is False
    assert created_streams[0].stopped is True
    assert created_streams[0].closed is True
    # Zero internal chunks retained & zero files written
    assert session._chunks == []
    assert list(tmp_path.iterdir()) == []

    # Cancel wipes buffered PCM cleanly
    session.start()
    session.push_test_samples(sample)
    session.cancel()
    assert session.stop_and_consume().size == 0


@pytest.mark.unit
def test_double_clap_detector_timing_and_noise_rejection() -> None:
    detector = DoubleClapDetector(
        DoubleClapConfig(
            rms_threshold=0.06,
            min_interval_s=0.1,
            max_interval_s=0.8,
            debounce_s=0.06,
        )
    )
    quiet = np.full(1024, 0.005, dtype=np.float32)
    loud = np.full(1024, 0.25, dtype=np.float32)

    assert detector.process_chunk(quiet, timestamp=1.0) is False
    assert detector.process_chunk(loud, timestamp=2.0) is False
    # Too quick (< 0.1s) should not trigger
    assert detector.process_chunk(loud, timestamp=2.07) is False
    # Valid second clap at +0.35s triggers
    assert detector.process_chunk(loud, timestamp=2.35) is True
    # Must wait for a fresh pair afterward
    assert detector.process_chunk(loud, timestamp=3.0) is False
    # Second clap > max_interval_s resets to first clap instead of false positive
    assert detector.process_chunk(loud, timestamp=4.2) is False

    # Monitor respects start/stop lifecycle
    streams: list[_FakeStream] = []
    detected = threading.Event()
    monitor = DoubleClapMonitor(
        DoubleClapConfig(rms_threshold=0.06, min_interval_s=0.1, max_interval_s=0.8),
        on_detected=detected.set,
        stream_factory=lambda **kw: streams.append(_FakeStream(**kw)) or streams[-1],
    )
    monitor.start()
    assert monitor.is_monitoring is True
    streams[0].callback(loud, 1024, None, None)
    monitor._detector._last_clap_ts -= 0.3
    monitor._detector._first_clap_ts -= 0.3
    streams[0].callback(loud, 1024, None, None)
    assert detected.is_set()
    monitor.stop()
    assert monitor.is_monitoring is False
    assert streams[0].stopped and streams[0].closed


@pytest.mark.unit
def test_voice_coordinator_opt_in_permission_and_prime_app_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_pywhispercpp(monkeypatch, transcript="Status report please")
    tts_state = _install_fake_avfaudio(monkeypatch)

    cfg = load_config(
        env={
            "PRIME_DATA_DIR": str(tmp_path / "data"),
            "PRIME_LOG_DIR": str(tmp_path / "logs"),
            "PRIME_ENVIRONMENT": "test",
        }
    )
    assert cfg.activation.double_clap_enabled is False

    stt_dir = tmp_path / "stt"
    stt_dir.mkdir(parents=True)
    stt_weight = stt_dir / "ggml-small-q5_1.bin"
    stt_weight.write_bytes(b"ggml" * 1024)

    prompted = {"count": 0}
    perm_state = {"value": PermissionState.NOT_DETERMINED}

    def _perm_check() -> PermissionState:
        return perm_state["value"]

    def _perm_req() -> PermissionState:
        prompted["count"] += 1
        return perm_state["value"]

    app = PrimeApp(cfg, platform_override="darwin")
    app._stt_registry = STTModelRegistry(stt_dir)
    app.voice = VoiceCoordinator(
        cfg.voice,
        app._stt_registry,
        double_clap_enabled=cfg.activation.double_clap_enabled,
        permission_checker=_perm_check,
        permission_requester=_perm_req,
        capture_factory=lambda **kw: AudioCaptureSession(
            AudioCaptureConfig(),
            stream_factory=lambda **skw: _FakeStream(**skw),
            on_level=kw.get("on_level"),
        ),
    )
    app.bootstrap()
    try:
        # 1. Double-clap is disabled by default and refused until opt-in
        with pytest.raises(VoicePipelineError):
            app.set_double_clap_monitoring(True, allow_prompt=False)
        assert prompted["count"] == 0

        # 2. Recording refuses without prompting when allow_prompt=False
        with pytest.raises(PermissionDeniedError):
            app.start_voice_recording(allow_prompt=False)
        assert prompted["count"] == 0

        # 3. Granting mic permission enables PTT -> STT -> Local LLM -> Local TTS
        perm_state["value"] = PermissionState.GRANTED
        fake_llm = _FakeLLM("System healthy on M1.")
        app.runtime._provider = fake_llm
        app.runtime._generation._provider = fake_llm
        app.runtime._state = RuntimeState.READY
        app.runtime._model_dir = tmp_path / "models"

        app.start_voice_recording(allow_prompt=False)
        assert app.state == AssistantState.LISTENING
        app.voice._capture.push_test_samples(np.full(4096, 0.2, dtype=np.float32))

        stt_res = app.stop_and_transcribe_voice()
        assert stt_res.text == "Status report please"
        assert app.state == AssistantState.IDLE

        reply = app.submit_text_message(stt_res.text)
        assert reply.assistant_text == "System healthy on M1."
        assert app.speak_reply(reply.assistant_text) is True
        # Fake AVSpeechSynthesizer completes cleanly after speakUtterance_
        assert tts_state["spoken"][-1][0] == "System healthy on M1."
        app.stop_speaking()
        assert app.state == AssistantState.IDLE
    finally:
        app.shutdown()


@pytest.mark.unit
def test_voice_config_toml_roundtrip_and_invalid_values(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        """
[activation]
double_clap_enabled = true
ptt_shortcut = "Alt+Space"

[voice]
stt_model_slug = "whisper-large-v3-turbo-q5_0"
tts_enabled = false
tts_english_voice = "Samantha"
tts_bangla_voice = "Piya"
tts_rate = 0.65
tts_volume = 0.75
""",
        encoding="utf-8",
    )
    cfg = load_config(
        config_path=cfg_file,
        env={"PRIME_DATA_DIR": str(tmp_path / "d"), "PRIME_LOG_DIR": str(tmp_path / "l")},
    )
    assert cfg.activation.double_clap_enabled is True
    assert cfg.activation.ptt_shortcut == "Alt+Space"
    assert cfg.voice.stt_model_slug == "whisper-large-v3-turbo-q5_0"
    assert cfg.voice.tts_enabled is False
    assert cfg.voice.tts_english_voice == "Samantha"
    assert cfg.voice.tts_rate == pytest.approx(0.65)
    assert cfg.voice.tts_volume == pytest.approx(0.75)

    # Disabling double-clap stops active monitoring immediately
    app = PrimeApp(cfg, platform_override="darwin")
    streams: list[_FakeStream] = []
    app.voice = VoiceCoordinator(
        cfg.voice,
        app._stt_registry,
        double_clap_enabled=True,
        permission_checker=lambda: PermissionState.GRANTED,
        capture_factory=lambda **kw: AudioCaptureSession(
            stream_factory=lambda **skw: _FakeStream(**skw), on_level=kw.get("on_level")
        ),
    )
    app.voice._clap_monitor = DoubleClapMonitor(
        stream_factory=lambda **kw: streams.append(_FakeStream(**kw)) or streams[-1],
    )
    app.bootstrap()
    try:
        assert app.set_double_clap_monitoring(True, allow_prompt=False) is True
        app.update_settings(double_clap_enabled=False, persist=False)
        assert app.get_voice_snapshot().double_clap_monitoring is False
        assert streams[0].stopped is True
    finally:
        app.shutdown()
