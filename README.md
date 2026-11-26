# PRIME

**PRIME** (`com.mrhrafi3.prime`) is an independent, 100% local personal AI assistant built for **macOS (Apple Silicon, M1 8 GB unified memory)** with **Bangla + English** language priority.

> **Current Status — Phase 05 (Voice Intelligence)**
> PRIME now provides **100% offline local voice interaction** alongside **offline MLX LLM inference** inside the **PySide6 / Qt Quick QML JARVIS HUD**: Push-to-Talk (`Ctrl+Space` or Hold button), opt-in Double-Clap transient detection (disabled by default), offline `whisper.cpp` STT (`whisper-small-q5_1` & `whisper-large-v3-turbo-q5_0` on Apple Metal), and offline macOS `AVSpeechSynthesizer` TTS (English + Bangla `Piya`). Zero audio files are written to disk and zero cloud AI/voice calls exist.
>
> **Deferred to Phase 06+:** Wake-word detection, on-demand camera/hand tracking, Screen OCR, and Windows system adapters.

---

## Implemented Features (Phases 02 – 05)

- **100% Offline Voice Intelligence (`prime.voice`):**
  - **Push-to-Talk & Bounded RAM Audio Capture (`sounddevice`):** 16 kHz mono float32 capture strictly in memory with live RMS meter (`0.0..1.0`), zero `.wav`/`.mp3` persistence, and immediate zero-fill cleanup after stop or cancel.
  - **Offline Whisper STT (`pywhispercpp`):** Local Metal-accelerated transcription with SHA-256 verified GGML weights under `~/Library/Application Support/PRIME/models/stt/`. For English-only speed, `whisper-small-q5_1` decodes at RTF `~0.16`; for **Bangla + English** accuracy, `whisper-large-v3-turbo-q5_0` decodes Bangla cleanly (`~2.4–2.7 s`) and runs alongside `Qwen2.5-1.5B-Instruct-4bit` within `~1.05 GB` peak process RSS.
  - **Offline macOS TTS (`AVFAudio.AVSpeechSynthesizer`):** Speaks replies off the UI thread with automatic Bangla script detection (`Piya`, `bn-IN`), configurable English voice (`Daniel`, `Samantha`, etc.), rate, volume, and immediate barge-in interruption.
  - **Opt-In Double-Clap (`DoubleClapDetector`):** Disabled by default (`double_clap_enabled = false`); no wake-word listener and no silent background mic capture at startup.
  - **Privacy-First Mic TCC:** Non-prompting macOS `AVCaptureDevice` status checks during diagnostics/tests; explicit permission prompt only upon user interaction.
- **100% Offline MLX Inference (`prime.intelligence`):**
  - `MLXProvider` (`HF_HUB_OFFLINE=1` enforced during inference) supporting token-by-token streaming, instant cancellation, and explicit Metal cache unloading (`0.0 MB` active after unload).
  - Curated M1 8 GB model registry (`ModelRegistry`) under `~/Library/Application Support/PRIME/models/` with path containment and zero automatic remote downloads.
  - External configurable system prompt (`prompts/system_prompt.md`) supporting Bangla, English, and Banglish.
  - Benchmarked on M1 8 GB with `Qwen2.5-1.5B-Instruct-4bit` (`~50–52 tok/s`, `1.24 GB` peak MLX) and `Qwen3-1.7B-4bit` (`~45–46 tok/s`, `1.38 GB` peak MLX).
- **JARVIS-Inspired Desktop UI (`prime.ui`):** Dark navy/cyan Qt Quick/QML HUD with real inference & voice states (`Idle`, `Listening`, `Transcribing`, `Thinking`, `Speaking`, `Error`), background `QThread` workers, Load/Unload/Stop controls, live waveform bar, Double-Clap indicator, and expanded Settings modal.
- **Typed Configuration & Redacted Logging (`prime.config`, `prime.logging`):** TOML/JSON config with `0700`/`0600` persistence, `PRIME_*` env overrides, rotating local logs with secret & private-prompt redaction.
- **Three-Tier Security & Platform Abstraction (`prime.security`, `prime.system`):** Tier 0/1/2 authorization, sandbox path validation, URL/app allowlists, OS-neutral `SystemController`, and `MacOSSystemController`.
- **Local SQLite + FTS5 Memory (`prime.intelligence.memory`):** Versioned migrations, parameterized SQL, `0600` DB permissions, and multi-turn `ContextAssembler`.

---

## Quick Start

```bash
uv sync --python 3.12 --group dev
uv run prime ui
```

CLI diagnostics & offline benchmark script (for already-installed approved models):

```bash
uv run prime --version
uv run prime config
uv run prime status
uv run prime doctor
uv run python scripts/benchmark_models.py
```

Run automated tests and static checks:

```bash
uv run pytest -v
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
```

---

## Documentation

- [Phase 05 Voice Architecture](phase-05-reports/VOICE_ARCHITECTURE.md)
- [Phase 05 STT Benchmark Report](phase-05-reports/STT_BENCHMARK_REPORT.md)
- [Phase 05 Voice Security Audit](phase-05-reports/VOICE_SECURITY_AUDIT.md)
- [Phase 05 Voice Setup Guide](phase-05-reports/VOICE_SETUP_GUIDE.md)
- [Phase 04 Implementation Plan](phase-04-reports/PHASE_04_IMPLEMENTATION_PLAN.md)
- [Local AI Architecture](phase-04-reports/LOCAL_AI_ARCHITECTURE.md)
- [Model Benchmark Report](phase-04-reports/MODEL_BENCHMARK_REPORT.md)
- [Model Installation Guide](phase-04-reports/MODEL_INSTALLATION_GUIDE.md)
- [Local AI Security Report](phase-04-reports/LOCAL_AI_SECURITY_REPORT.md)
- [Local AI Performance Report](phase-04-reports/LOCAL_AI_PERFORMANCE_REPORT.md)
- [UI Architecture (Phase 03)](phase-03-reports/UI_ARCHITECTURE.md)
- [Core Architecture (Phase 02)](docs/ARCHITECTURE.md)
- [Third-Party Notices & Attribution](THIRD_PARTY_NOTICES.md)
- [Changelog](CHANGELOG.md)

## License

Newly authored PRIME code is licensed under the [MIT License](LICENSE) (`Copyright (c) 2026 MrhRafi3`). `mlx` / `mlx-lm` are MIT; `PySide6` / Qt6 is used dynamically under LGPLv3; `VISION-1.2` (MIT) foundational attribution is preserved in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
