# PRIME — Phase 05 Implementation Plan (Voice Intelligence)

**Product:** PRIME (`com.mrhrafi3.prime`)  
**GitHub:** `https://github.com/MrhRafi3/PRIME` (`main` at `25ad9edadbd67da162b6dc149b554d8817ca6d53`)  
**Target Hardware:** Apple Silicon MacBook Air M1, 8 GB Unified Memory (`macOS 27.2.1`)  
**Date:** 2026-11-26  

---

## 1. Initial Audit Findings

- **Git & Remote State:** Clean working tree on `main`, up to date with `origin/main` (`https://github.com/MrhRafi3/PRIME.git`).
- **Existing Voice Scaffolding:** `src/prime/voice/contracts.py` already defines `SpeechLanguage`, `AudioPolicy` (`wake_word_enabled=False`, `background_recording_allowed=False`, `log_raw_audio=False`), `STTProvider`, `TTSProvider`, `ActivationSnapshot`, and `ActivationStatus`. `PrimeApp` already implements `set_push_to_talk()` and `update_settings(double_clap_enabled=...)`, and `Main.qml` / `SettingsDialog.qml` already render Push-to-Talk and Double-Clap UI controls.
- **Verified Local macOS Voices (`say -v ?`):**
  - **Bangla (`bn_IN`):** `Piya` is already installed locally on this Mac.
  - **English (`en_US`, `en_GB`, `en_IN`):** `Samantha`, `Daniel`, `Alex`, `Rishi`, `Aman`, `Tara`, and others are already installed locally.
- **STT Dependency Comparison:**
  - `mlx-whisper` (`0.4.3`, MIT) pulls 45 packages including `torch==2.15.0`, `numba`, `llvmlite`, `scipy`, and `sympy`.
  - `pywhispercpp` (`1.5.1`, MIT) pulls 18 packages total (zero `torch` bloat), runs `whisper.cpp` locally on Apple Silicon, and uses compact quantized GGML models (`~181 MiB` to `~547 MiB`).

---

## 2. Implementation Milestones

1. **Approval Gate (Before Installs/Downloads):** Obtain explicit user approval for audio/STT/TTS dependencies (`pywhispercpp` or `mlx-whisper`, `sounddevice`, `pyobjc-framework-AVFoundation`) and candidate STT model weights.
2. **Audio I/O & Permissions (`src/prime/voice/audio.py`, `permissions.py`):**
   - Non-prompting TCC Microphone status check + explicit user-triggered request via `AVCaptureDevice` (`AVFoundation`).
   - Bounded, in-memory `sounddevice` PCM capture (16 kHz mono float32/int16) with live RMS level stream (`0.0..1.0`), recording duration counter, zero raw audio disk persistence, and immediate buffer wipe after transcription.
3. **Offline STT (`src/prime/voice/stt/`):**
   - `STTProvider` implementation (`WhisperCppSTTProvider` / `MLXWhisperSTTProvider`) supporting Bangla (`bn`), English (`en`), auto `bn-en` detection, lazy loading, cancellation, silence/empty-audio guard, and explicit `unload()`.
   - Benchmark 2 practical M1 8 GB models (e.g., `small-q5_1` vs `large-v3-turbo-q5_0`) across Bangla, English, and Banglish alone and alongside loaded `qwen2.5-1.5b-4bit`.
4. **Offline TTS (`src/prime/voice/tts/`):**
   - `AVSpeechTTSProvider` using macOS `AVSpeechSynthesizer` (`Piya` for Bangla script, user-selected English voice such as `Daniel`/`Samantha` for English), adjustable speech rate & volume, start/stop/cancel controls, zero cloud fallback.
5. **Push-to-Talk & Double-Clap Activation (`src/prime/voice/activation/`):**
   - Push-to-Talk: Hold/toggle record -> cancel or release -> transcribe -> submit to `PrimeApp.submit_text_message()` -> stream local LLM reply -> optionally speak reply via offline TTS.
   - Double-Clap: Disabled by default; explicit opt-in in Settings; lightweight streaming RMS transient detector with configurable threshold and min/max interval (`0.1s–0.8s`), anti-noise debounce, zero audio persistence, immediate stop when disabled, and visible monitoring indicator.
6. **UI & Core Wiring (`PrimeApp`, `PrimeUIBridge`, `Main.qml`, `SettingsDialog.qml`):**
   - Integrate `Idle`, `Listening`, `Transcribing`, `Thinking`, `Speaking`, `Error` states, live mic waveform/meter, recording timer, transcript preview, Stop/Cancel controls, TTS voice/rate/volume controls, microphone permission badge, and double-clap monitoring indicator.
7. **Verification & Publishing:** Run full offline/mocked `pytest` suite, `ruff`, `prime doctor`, live benchmarks, security audit, write all 6 Phase 05 reports, commit cleanly, and push normally to `origin/main`.
