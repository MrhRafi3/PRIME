"""Opt-in local double-clap transient detector (zero recording persistence, no wake-word)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from prime.voice.audio_capture import compute_rms
from prime.voice.contracts import VoicePipelineError


@dataclass(frozen=True, slots=True)
class DoubleClapConfig:
    """Sensitivity and timing bounds for transient double-clap detection."""

    # Normalized float32 RMS threshold (default ~0.061 corresponds to ~2000/32768 int16)
    rms_threshold: float = 0.061
    min_interval_s: float = 0.1
    max_interval_s: float = 0.8
    debounce_s: float = 0.06
    noise_floor_multiplier: float = 3.0
    sample_rate: int = 16000
    block_size: int = 1024


class DoubleClapDetector:
    """Stateless-audio transient detector that discards every frame immediately."""

    def __init__(self, config: DoubleClapConfig | None = None) -> None:
        self._config = config or DoubleClapConfig()
        self._clap_count = 0
        self._first_clap_ts = 0.0
        self._last_clap_ts = 0.0
        self._noise_floor = 0.005

    @property
    def config(self) -> DoubleClapConfig:
        return self._config

    def reset(self) -> None:
        self._clap_count = 0
        self._first_clap_ts = 0.0
        self._last_clap_ts = 0.0

    def process_chunk(self, samples: np.ndarray, *, timestamp: float | None = None) -> bool:
        """Analyze a single short PCM frame in RAM and return True on double clap."""
        now = time.monotonic() if timestamp is None else timestamp
        rms = compute_rms(samples)

        if self._clap_count == 1 and (now - self._first_clap_ts) > self._config.max_interval_s:
            self._clap_count = 0

        dynamic_floor = max(
            self._config.rms_threshold,
            self._noise_floor * self._config.noise_floor_multiplier,
        )
        is_transient = rms > dynamic_floor

        if not is_transient:
            # Smoothly adapt ambient noise floor only on non-transient frames
            self._noise_floor = (self._noise_floor * 0.92) + (rms * 0.08)
            return False

        if (now - self._last_clap_ts) < self._config.debounce_s:
            return False

        self._last_clap_ts = now
        if self._clap_count == 0:
            self._clap_count = 1
            self._first_clap_ts = now
            return False

        elapsed = now - self._first_clap_ts
        if elapsed < self._config.min_interval_s:
            return False
        if elapsed <= self._config.max_interval_s:
            self.reset()
            return True

        # Too slow: treat as a new first clap
        self._clap_count = 1
        self._first_clap_ts = now
        return False


class DoubleClapMonitor:
    """Opt-in live microphone transient monitor (disabled by default)."""

    def __init__(
        self,
        config: DoubleClapConfig | None = None,
        *,
        on_detected: Callable[[], None] | None = None,
        stream_factory: Callable[..., Any] | None = None,
    ) -> None:
        self._detector = DoubleClapDetector(config)
        self._on_detected = on_detected
        self._stream_factory = stream_factory
        self._lock = threading.Lock()
        self._stream: Any = None
        self._active = False

    @property
    def is_monitoring(self) -> bool:
        return self._active

    def start(self) -> None:
        with self._lock:
            if self._active:
                return
            self._detector.reset()
            cfg = self._detector.config
            if self._stream_factory is not None:
                stream = self._stream_factory(
                    samplerate=cfg.sample_rate,
                    channels=1,
                    blocksize=cfg.block_size,
                    dtype="float32",
                    callback=self._callback,
                )
            else:
                import sounddevice as sd

                stream = sd.InputStream(
                    samplerate=cfg.sample_rate,
                    channels=1,
                    blocksize=cfg.block_size,
                    dtype="float32",
                    callback=self._callback,
                )
            try:
                stream.start()
            except Exception as exc:
                raise VoicePipelineError(
                    f"Failed to start double-clap monitoring stream: {exc}"
                ) from exc
            self._stream = stream
            self._active = True

    def _callback(self, indata: np.ndarray, _frames: int, _time_info: Any, _status: Any) -> None:
        if not self._active:
            return
        mono = np.asarray(indata, dtype=np.float32).reshape(-1)
        if self._detector.process_chunk(mono) and self._on_detected is not None:
            self._on_detected()

    def stop(self) -> None:
        with self._lock:
            self._active = False
            self._detector.reset()
            if self._stream is not None:
                try:
                    self._stream.stop()
                finally:
                    try:
                        self._stream.close()
                    finally:
                        self._stream = None
