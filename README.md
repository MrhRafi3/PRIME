# PRIME

**PRIME** (`com.mrhrafi3.prime`) is an independent, 100% local personal AI assistant built for **macOS (Apple Silicon, M1 8 GB unified memory)** with **Bangla + English** language priority.

> **Current Status — Phase 04 (Local AI Intelligence Engine)**
> PRIME runs **100% offline local LLM inference** on Apple Silicon via **MLX-LM** (`mlx 0.32.5`, `mlx-lm 0.32.2`) integrated into the **PySide6 / Qt Quick QML JARVIS HUD**, with local SQLite + FTS5 multi-turn conversation memory, lazy model loading, token streaming, generation cancellation, and M1 8 GB memory budget enforcement.
>
> **Deferred to Phase 05+:** Real microphone capture, offline speech-to-text, offline text-to-speech, double-clap audio detection, wake-word detection, on-demand camera/hand tracking, Screen OCR, and Windows system adapters.

---

## Implemented Features (Phases 02 – 04)

- **100% Offline MLX Inference (`prime.intelligence`):**
  - `MLXProvider` (`HF_HUB_OFFLINE=1` enforced during inference) supporting token-by-token streaming, instant cancellation, and explicit Metal cache unloading (`0.0 MB` active after unload).
  - Curated M1 8 GB model registry (`ModelRegistry`) under `~/Library/Application Support/PRIME/models/` with path containment and zero automatic remote downloads.
  - External configurable system prompt (`prompts/system_prompt.md`) supporting Bangla, English, and Banglish.
  - Benchmarked on M1 8 GB with `Qwen2.5-1.5B-Instruct-4bit` (`~50–52 tok/s`, `1.24 GB` peak MLX) and `Qwen3-1.7B-4bit` (`~45–46 tok/s`, `1.38 GB` peak MLX).
- **JARVIS-Inspired Desktop UI (`prime.ui`):** Dark navy/cyan Qt Quick/QML HUD with real inference states (`Model Not Installed`, `Model Available`, `Loading Model`, `Ready`, `Thinking`, `Streaming Response`, `Cancelling`, `Error`), background `QThread` inference & telemetry, Load/Unload & Stop controls, live `tok/s` & token count, and Settings modal.
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
