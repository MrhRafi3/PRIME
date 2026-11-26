# PRIME — Phase 05 Offline TTS Quality Report

**Implementation:** `AVSpeechTTSProvider` (`src/prime/voice/tts/avspeech_provider.py`)  
**Backend:** macOS `AVFAudio.AVSpeechSynthesizer` via `pyobjc-framework-AVFoundation==13.1`  
**Operating Mode:** 100% Local CoreAudio synthesis; zero cloud APIs or network calls

---

## 1. Locally Installed Offline Voices Verified

Queried locally from `AVFAudio.AVSpeechSynthesisVoice.speechVoices()`:
- **Total system voices present:** `180`
- **English voices present (`en-*`):** `41` (including `Daniel` [`en-GB`], `Samantha` [`en-US`], `Alex`, `Rishi` [`en-IN`], `Aman`, `Tara`, plus Eloquence/novelty variants)
- **Bangla voice present (`bn-*`):** `1` — **`Piya`** (`com.apple.voice.compact.bn-IN.Paya`, `bn-IN`)

---

## 2. Routing, Latency & Feature Verification

| Capability | Verification Result | Notes |
| :--- | :--- | :--- |
| English synthesis (`Daniel`) | **Pass** (`101.7 ms` for `"Offline voice check."` return/handoff) | Clear, natural pronunciation; crisp pacing |
| Bangla script routing (`[\u0980-\u09FF]`) | **Pass** (`4,122.9 ms` full utterance playback for `"অফলাইন বাংলা পরীক্ষা।"`) | Automatic switch to `Piya` when Bangla script is detected |
| Mixed Bangla/English fallback | **Pass** | Auto-mode uses `Piya` for Bangla sentences and user-configured English voice (default `Daniel`) for English sentences |
| Rate & volume control | **Pass** | Normalized `[0.1..1.0]` rate mapped between `AVSpeechUtteranceMinimumSpeechRate` and `AVSpeechUtteranceMaximumSpeechRate`; volume `[0.0..1.0]` |
| Cancellation / Barge-in | **Pass** | `AVSpeechSynthesizer.stopSpeakingAtBoundary_(AVSpeechBoundaryImmediate)` cancels playback immediately on Stop click or PTT start |
| UI-thread non-blocking behavior | **Pass** | Playback runs via CoreAudio + daemon monitor thread; UI stays responsive |

---

## 3. Known Limitations (Documented Honestly)

1. **`Piya` (`bn-IN` compact):** Only the built-in compact voice (`bn-IN`) is installed on macOS out of the box. Its prosody reflects Indian Bengali pronunciation rather than Bangladeshi Dhaka dialect, and romanized Banglish sentences written in ASCII are read with the selected English voice (`Daniel`/`Samantha`).
2. **Code-mixed sentences:** `AVSpeechUtterance` selects one voice per utterance. Sentences containing mostly English plus a Bangla word route to `Piya` (due to `contains_bangla()`), whereas pure ASCII Banglish routes to the English voice.
3. **No synthesized PCM file caching:** `AVSpeechTTSProvider` speaks directly through macOS CoreAudio with zero WAV artifacts saved to disk, which strengthens privacy cleanly.
