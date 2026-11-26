"""Bounded in-memory microphone audio capture with zero disk persistence."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from prime.voice.contracts import VoicePipelineError


@dataclass(frozen=True, slots=True)
class AudioCaptureConfig:
    sample_rate: int = 16000
    channels: int = 1
    block_size: int = 1024
    max_duration_s: float = 30.0
    silence_rms_threshold: float = 0.004


def compute_rms(samples: np.ndarray) -> float:
    """Compute normalized RMS amplitude (0.0..1.0) for mono float32 PCM samples."""
    if samples.size == 0:
        return 0.0
    arr = np.asarray(samples, dtype=np.float32)
    return float(np.sqrt(np.mean(np.square(arr))))


def is_silent(samples: np.ndarray, *, threshold: float = 0.004) -> bool:
    """Return True if audio is empty or below the minimum speech RMS threshold."""
    return samples.size == 0 or compute_rms(samples) < threshold


class AudioCaptureSession:
    """Captures bounded 16 kHz mono PCM strictly in RAM for push-to-talk."""

    def __init__(
        self,
        config: AudioCaptureConfig | None = None,
        *,
        stream_factory: Callable[..., Any] | None = None,
        on_level: Callable[[float, float], None] | None = None,
    ) -> None:
        self._config = config or AudioCaptureConfig()
        self._stream_factory = stream_factory
        self._on_level = on_level
        self._lock = threading.Lock()
        self._chunks: list[np.ndarray] = []
        self._total_samples = 0
        self._max_samples = int(self._config.sample_rate * self._config.max_duration_s)
        self._stream: Any = None
        self._active = False
        self._cancelled = False
        self._start_time = 0.0

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def elapsed_seconds(self) -> float:
        if not self._active:
            return 0.0
        return max(0.0, time.monotonic() - self._start_time)

    def start(self) -> None:
        with self._lock:
            if self._active:
                return
            self._wipe_buffers_locked()
            self._cancelled = False
            self._start_time = time.monotonic()

            if self._stream_factory is not None:
                stream = self._stream_factory(
                    samplerate=self._config.sample_rate,
                    channels=self._config.channels,
                    blocksize=self._config.block_size,
                    dtype="float32",
                    callback=self._audio_callback,
                )
            else:
                import sounddevice as sd

                stream = sd.InputStream(
                    samplerate=self._config.sample_rate,
                    channels=self._config.channels,
                    blocksize=self._config.block_size,
                    dtype="float32",
                    callback=self._audio_callback,
                )

            try:
                stream.start()
            except Exception as exc:
                self._wipe_buffers_locked()
                raise VoicePipelineError(f"Failed to start microphone stream: {exc}") from exc

            self._stream = stream
            self._active = True

    def _audio_callback(
        self,
        indata: np.ndarray,
        _frames: int,
        _time_info: Any,
        status: Any,
    ) -> None:
        _ = status
        mono = np.asarray(indata, dtype=np.float32).reshape(-1).copy()
        rms = compute_rms(mono)
        elapsed = 0.0

        with self._lock:
            if not self._active or self._cancelled:
                return
            remaining = self._max_samples - self._total_samples
            if remaining > 0:
                clipped = mono[:remaining]
                self._chunks.append(clipped)
                self._total_samples += clipped.size
            elapsed = max(0.0, time.monotonic() - self._start_time)

        if self._on_level is not None:
            self._on_level(min(1.0, rms * 6.0), elapsed)

    def push_test_samples(self, samples: np.ndarray) -> None:
        """Feed deterministic audio samples in unit tests without opening hardware."""
        self._audio_callback(samples, len(samples), None, None)

    def stop_and_consume(self) -> np.ndarray:
        """Stop capture, concatenate buffered PCM, and immediately wipe internal buffers."""
        with self._lock:
            self._close_stream_locked()
            if self._cancelled or not self._chunks:
                self._wipe_buffers_locked()
                return np.empty(0, dtype=np.float32)
            audio = np.concatenate(self._chunks).astype(np.float32, copy=False)
            self._wipe_buffers_locked()
            return audio

    def cancel(self) -> None:
        """Abort capture immediately and scrub all buffered audio from memory."""
        with self._lock:
            self._cancelled = True
            self._close_stream_locked()
            self._wipe_buffers_locked()

    def _close_stream_locked(self) -> None:
        self._active = False
        if self._stream is not None:
            try:
                self._stream.stop()
            finally:
                try:
                    self._stream.close()
                finally:
                    self._stream = None

    def _wipe_buffers_locked(self) -> None:
        for chunk in self._chunks:
            chunk.fill(0.0)
        self._chunks.clear()
        self._total_samples = 0
