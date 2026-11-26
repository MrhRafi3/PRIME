"""Offline whisper.cpp STT provider operating strictly on in-memory PCM audio."""

from __future__ import annotations

import gc
import os
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

from prime.voice.audio_capture import is_silent
from prime.voice.contracts import SpeechLanguage, STTResult, VoicePipelineError


class WhisperCppSTTProvider:
    """Offline Whisper.cpp provider via pywhispercpp (no cloud calls, no temp files)."""

    def __init__(self, *, n_threads: int = 4, silence_threshold: float = 0.004) -> None:
        self._n_threads = max(1, min(8, int(n_threads)))
        self._silence_threshold = silence_threshold
        self._lock = threading.RLock()
        self._model: Any = None
        self._active_slug: str | None = None
        self._cancel_event = threading.Event()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def active_model_id(self) -> str | None:
        return self._active_slug

    def load(self, slug: str, model_path: Path) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Local STT model file not found at {model_path!s}. Approval required to download."
            )
        with self._lock:
            self.unload()
            os.environ["HF_HUB_OFFLINE"] = "1"
            try:
                from pywhispercpp.model import Model

                self._model = Model(
                    model=str(model_path),
                    n_threads=self._n_threads,
                    print_realtime=False,
                    print_progress=False,
                    print_timestamps=False,
                    redirect_whispercpp_logs_to=False,
                )
                self._active_slug = slug
            except Exception as exc:
                self._model = None
                self._active_slug = None
                raise VoicePipelineError(f"Failed to load local STT model '{slug}': {exc}") from exc

    def unload(self) -> None:
        with self._lock:
            self._cancel_event.set()
            self._model = None
            self._active_slug = None
            gc.collect()

    def cancel(self) -> None:
        self._cancel_event.set()

    def transcribe_array(
        self,
        samples: np.ndarray,
        *,
        sample_rate: int = 16000,
        language: SpeechLanguage = SpeechLanguage.AUTO_BN_EN,
        cancel_event: threading.Event | None = None,
    ) -> STTResult:
        """Transcribe 16 kHz mono float32 PCM samples strictly locally."""
        if not self.is_loaded:
            raise VoicePipelineError("No local STT model is currently loaded.")
        if sample_rate != 16000:
            raise VoicePipelineError(f"Expected 16000 Hz PCM audio, got {sample_rate} Hz.")

        arr = np.asarray(samples, dtype=np.float32).reshape(-1)
        if is_silent(arr, threshold=self._silence_threshold):
            return STTResult(text="", language=language, confidence=0.0, duration_ms=0)

        self._cancel_event.clear()
        start = time.perf_counter()

        def _should_abort() -> bool:
            return self._cancel_event.is_set() or (
                cancel_event is not None and cancel_event.is_set()
            )

        kwargs: dict[str, Any] = {
            "abort_callback": _should_abort,
            "n_threads": self._n_threads,
        }
        if language == SpeechLanguage.BANGLA:
            kwargs["language"] = "bn"
        elif language == SpeechLanguage.ENGLISH:
            kwargs["language"] = "en"
        else:
            kwargs["language"] = "auto"

        with self._lock:
            if self._model is None:
                raise VoicePipelineError("STT model was unloaded before transcription.")
            try:
                segments = self._model.transcribe(arr, **kwargs)
            except Exception as exc:
                if _should_abort():
                    return STTResult(text="", language=language, confidence=0.0, duration_ms=0)
                raise VoicePipelineError(f"Local STT transcription failed: {exc}") from exc

        if _should_abort():
            return STTResult(text="", language=language, confidence=0.0, duration_ms=0)

        text = " ".join(str(getattr(seg, "text", "")).strip() for seg in segments).strip()
        duration_ms = int((time.perf_counter() - start) * 1000)
        return STTResult(
            text=text,
            language=language,
            confidence=1.0 if text else 0.0,
            duration_ms=duration_ms,
        )

    def transcribe_pcm(self, pcm_bytes: bytes, *, sample_rate: int = 16000) -> STTResult:
        """Protocol method accepting raw int16 little-endian PCM bytes in memory."""
        if not pcm_bytes:
            return STTResult(
                text="",
                language=SpeechLanguage.AUTO_BN_EN,
                confidence=0.0,
                duration_ms=0,
            )
        int16_arr = np.frombuffer(pcm_bytes, dtype=np.int16)
        float_arr = int16_arr.astype(np.float32) / 32768.0
        return self.transcribe_array(float_arr, sample_rate=sample_rate)
