"""Offline Text-to-Speech providers for PRIME."""

from prime.voice.tts.avspeech_provider import AVSpeechTTSProvider, LocalVoiceInfo, contains_bangla

__all__ = ["AVSpeechTTSProvider", "LocalVoiceInfo", "contains_bangla"]
