"""Offline macOS Text-to-Speech via AVFAudio AVSpeechSynthesizer."""

from __future__ import annotations

import contextlib
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from prime.voice.contracts import SpeechLanguage, VoicePipelineError

_BANGLA_SCRIPT_RE = re.compile(r"[\u0980-\u09FF]")


@dataclass(frozen=True, slots=True)
class LocalVoiceInfo:
    name: str
    identifier: str
    language: str


def contains_bangla(text: str) -> bool:
    """Return True if text contains Unicode Bengali characters."""
    return _BANGLA_SCRIPT_RE.search(text) is not None


class AVSpeechTTSProvider:
    """100% offline macOS AVSpeechSynthesizer provider supporting English and Bangla."""

    def __init__(
        self,
        *,
        english_voice: str = "Daniel",
        bangla_voice: str = "Piya",
        rate: float = 0.5,
        volume: float = 0.9,
    ) -> None:
        self._english_voice = english_voice
        self._bangla_voice = bangla_voice
        self._rate = max(0.1, min(1.0, float(rate)))
        self._volume = max(0.0, min(1.0, float(volume)))
        self._lock = threading.RLock()
        self._synth = None
        self._speaking = False
        self._stop_event = threading.Event()
        self._speak_thread: threading.Thread | None = None

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    @property
    def english_voice(self) -> str:
        return self._english_voice

    @property
    def bangla_voice(self) -> str:
        return self._bangla_voice

    @property
    def rate(self) -> float:
        return self._rate

    @property
    def volume(self) -> float:
        return self._volume

    def configure(
        self,
        *,
        english_voice: str | None = None,
        bangla_voice: str | None = None,
        rate: float | None = None,
        volume: float | None = None,
    ) -> None:
        if english_voice is not None and english_voice.strip():
            self._english_voice = english_voice.strip()
        if bangla_voice is not None and bangla_voice.strip():
            self._bangla_voice = bangla_voice.strip()
        if rate is not None:
            self._rate = max(0.1, min(1.0, float(rate)))
        if volume is not None:
            self._volume = max(0.0, min(1.0, float(volume)))

    def list_voices(self, *, language_prefix: str = "") -> tuple[LocalVoiceInfo, ...]:
        """List locally installed AVSpeechSynthesisVoice entries offline."""
        try:
            import AVFAudio
        except Exception as exc:
            raise VoicePipelineError(f"AVFAudio unavailable: {exc}") from exc

        prefix = language_prefix.strip().lower()
        voices = []
        for voice in AVFAudio.AVSpeechSynthesisVoice.speechVoices():
            lang = str(voice.language())
            if prefix and not lang.lower().startswith(prefix):
                continue
            voices.append(
                LocalVoiceInfo(
                    name=str(voice.name()),
                    identifier=str(voice.identifier()),
                    language=lang,
                )
            )
        return tuple(voices)

    def _resolve_voice(self, text: str, language: SpeechLanguage):
        import AVFAudio

        use_bangla = language == SpeechLanguage.BANGLA or (
            language == SpeechLanguage.AUTO_BN_EN and contains_bangla(text)
        )
        all_voices = list(AVFAudio.AVSpeechSynthesisVoice.speechVoices())
        if not all_voices:
            raise VoicePipelineError("No offline AVSpeechSynthesisVoice voices available.")

        if use_bangla:
            for v in all_voices:
                if str(v.name()).lower() == self._bangla_voice.lower():
                    return v
            for v in all_voices:
                if str(v.language()).lower().startswith("bn"):
                    return v
            # Honest fallback to default English voice only if no local Bangla voice exists
        for v in all_voices:
            if str(v.name()).lower() == self._english_voice.lower():
                return v
        for v in all_voices:
            if str(v.language()).lower().startswith("en"):
                return v
        return AVFAudio.AVSpeechSynthesisVoice.voiceWithLanguage_("en-US")

    def speak(
        self,
        text: str,
        *,
        language: SpeechLanguage = SpeechLanguage.AUTO_BN_EN,
        on_finished: Callable[[], None] | None = None,
        blocking: bool = False,
    ) -> bool:
        """Speak text locally using AVSpeechSynthesizer without blocking UI thread."""
        clean = text.strip()
        if not clean:
            if on_finished is not None:
                on_finished()
            return False

        self.stop()
        try:
            import AVFAudio
        except Exception as exc:
            raise VoicePipelineError(f"AVFAudio unavailable: {exc}") from exc

        with self._lock:
            if self._synth is None:
                self._synth = AVFAudio.AVSpeechSynthesizer.alloc().init()
            utterance = AVFAudio.AVSpeechUtterance.speechUtteranceWithString_(clean)
            voice = self._resolve_voice(clean, language)
            if voice is not None:
                utterance.setVoice_(voice)

            min_rate = float(AVFAudio.AVSpeechUtteranceMinimumSpeechRate)
            max_rate = float(AVFAudio.AVSpeechUtteranceMaximumSpeechRate)
            mapped_rate = min_rate + (max_rate - min_rate) * self._rate
            utterance.setRate_(mapped_rate)
            utterance.setVolume_(self._volume)

            self._stop_event.clear()
            self._speaking = True
            self._synth.speakUtterance_(utterance)

        def _wait_loop() -> None:
            try:
                while not self._stop_event.is_set():
                    synth = self._synth
                    if synth is None or not bool(synth.isSpeaking()):
                        break
                    time.sleep(0.05)
            finally:
                self._speaking = False
                if on_finished is not None:
                    on_finished()

        if blocking:
            _wait_loop()
        else:
            t = threading.Thread(target=_wait_loop, daemon=True)
            self._speak_thread = t
            t.start()
        return True

    def stop(self) -> None:
        """Immediately cancel ongoing local speech synthesis."""
        self._stop_event.set()
        with self._lock:
            if self._synth is not None and bool(self._synth.isSpeaking()):
                import AVFAudio

                with contextlib.suppress(Exception):
                    self._synth.stopSpeakingAtBoundary_(AVFAudio.AVSpeechBoundaryImmediate)
            self._speaking = False

    def synthesize_to_pcm(self, text: str, *, language: SpeechLanguage) -> bytes:
        """Protocol method: AVSpeechSynthesizer speaks directly via CoreAudio."""
        self.speak(text, language=language, blocking=True)
        return b""
