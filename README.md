# PRIME

**PRIME** (`com.mrhrafi3.prime`) is an independent, local-first personal AI assistant project built for **macOS (Apple Silicon, M1 8 GB unified memory)** with **100% local AI** and **Bangla + English** language priority.

> **Current Status — Phase 02 (Foundation & Core Infrastructure)**
> PRIME is currently at the **Phase 02 architectural foundation** stage (`v0.1.0`). Core infrastructure, typed configuration, redacted structured logging, three-tier security/permission enforcement, platform abstraction (`SystemController`), macOS foundation adapter, and SQLite + FTS5 local memory are implemented and tested.
>
> **Not Yet Implemented:** Local LLM inference runtime (MLX / llama.cpp), offline speech-to-text, offline text-to-speech, push-to-talk / double-clap audio capture, JARVIS Qt Quick/QML desktop UI, camera/hand tracking, Screen OCR, and Windows system adapters are scheduled for Phase 03+.

---

## Implemented Foundation (Phase 02)

- **Typed Configuration (`prime.config`):** Dataclass-based configuration with TOML/JSON file loading, `PRIME_*` environment variable overrides, hardware memory profiles (`eco`, `balanced`, `heavy`), and strict local-only validation.
- **Secure Structured Logging (`prime.logging`):** Rotating local JSON/text log files (`0700` dir / `0600` file) with automatic secret/token redaction and private-content suppression by default.
- **Permission & Security Manager (`prime.security`):** Three-tier risk enforcement (`Tier 0` read-only, `Tier 1` reversible, `Tier 2` explicit user confirmation), strict sandbox path traversal protection, URL scheme validation, and application allowlisting.
- **Platform Abstraction Layer (`prime.system`):** OS-neutral `SystemController` interface with a safe `MacOSSystemController` foundation (`sysctl`, `pmset`, bounded `osascript` audio volume, allowlisted `open -a`, sandboxed folder creation) and a clear boundary for future Windows support.
- **Local SQLite + FTS5 Memory (`prime.intelligence.memory`):** Versioned SQLite migrations, parameterized queries, `0600` database file permissions, full-text search via FTS5, and explicit opt-in controls preventing automatic storage of sensitive personal data.
- **Core Lifecycle & Contracts (`prime.core`, `prime.intelligence`, `prime.voice`, `prime.vision`, `prime.plugins`):** Event bus, application bootstrap/shutdown, bounded multi-turn `ContextAssembler`, and typed contracts for upcoming AI, voice, vision, and plugin subsystems.

---

## Quick Start (Phase 02 Diagnostics)

```bash
uv sync --group dev
uv run prime --version
uv run prime config
uv run prime status
uv run prime doctor
```

Run the automated test suite and linter:

```bash
uv run pytest
uv run ruff check src tests
```

---

## Known Limitations (Phase 02)

- **No AI / Voice / UI Runtime Yet:** Local LLM (`mlx-lm` / `llama.cpp`), offline STT/TTS, audio activation, and Qt Quick/QML HUD are not installed or active in Phase 02.
- **macOS Only Today:** Non-macOS hosts cleanly raise `UnsupportedPlatformError`; Windows adapter implementation is deferred.
- **No Unprompted Hardware TCC Requests:** Microphone, Camera, Screen Recording, and Automation permission scopes intentionally report `not_determined` until their respective features are implemented.

---

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Development Setup](docs/DEVELOPMENT_SETUP.md)
- [Security Model](docs/SECURITY.md)
- [Third-Party Notices & Attribution](THIRD_PARTY_NOTICES.md)
- [Changelog](CHANGELOG.md)

## License

Newly authored PRIME code is licensed under the [MIT License](LICENSE) (`Copyright (c) 2026 MrhRafi3`). Foundational research drew from `VISION-1.2` (MIT); see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for full attribution details.
