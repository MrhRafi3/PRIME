# PRIME

**PRIME** (`com.mrhrafi3.prime`) is an independent, local-first personal AI assistant project built for **macOS (Apple Silicon, M1 8 GB unified memory)** with **100% local AI** and **Bangla + English** language priority.

> **Current Status — Phase 03 (JARVIS Desktop UI Foundation)**
> PRIME now includes a launchable **PySide6 / Qt Quick QML desktop HUD** (`uv run prime ui`) connected to the Phase 02 core architecture (`PrimeUIBridge`, background system telemetry, local SQLite message persistence, push-to-talk UI state transitions, and persistent settings).
>
> **Not Yet Implemented:** Local LLM inference runtime (MLX / llama.cpp), real microphone audio capture, offline speech-to-text, offline text-to-speech, double-clap audio detection, camera/hand tracking, Screen OCR, and Windows system adapters remain scheduled for Phase 04+. When a message is submitted in the UI today, PRIME records it locally and displays an explicit offline/not-connected notice without fabricating AI replies.

---

## Implemented Features (Phase 02 + Phase 03)

- **JARVIS-Inspired Desktop UI (`prime.ui`):** Dark navy/cyan Qt Quick/QML HUD with animated state core (`Idle`, `Listening`, `Processing`, `Speaking`), conversation log with Enter-to-send, Push-to-Talk UI state control, live CPU/Memory/Battery telemetry, local-only privacy footer, and Settings modal.
- **Typed Configuration (`prime.config`):** Dataclass-based configuration with TOML/JSON loading, atomic `0700`/`0600` TOML persistence, `PRIME_*` environment overrides, hardware memory profiles (`eco`, `balanced`, `heavy`), and strict local-only validation.
- **Secure Structured Logging (`prime.logging`):** Rotating local JSON/text log files (`0700` dir / `0600` file) with automatic secret/token redaction and private-content suppression by default.
- **Permission & Security Manager (`prime.security`):** Three-tier risk enforcement (`Tier 0/1/2`), sandbox path traversal protection, URL validation, and application allowlisting.
- **Platform Abstraction Layer (`prime.system`):** OS-neutral `SystemController` interface with `MacOSSystemController` (`sysctl`, `vm_stat`, `pmset`, bounded `osascript` volume, allowlisted `open -a`, sandboxed folders) and a clean boundary for future Windows support.
- **Local SQLite + FTS5 Memory (`prime.intelligence.memory`):** Versioned migrations, parameterized SQL, `0600` DB permissions, FTS5 search, and explicit sensitivity guards.

---

## Quick Start

```bash
uv sync --python 3.12 --group dev
uv run prime ui
```

CLI diagnostics:

```bash
uv run prime --version
uv run prime config
uv run prime status
uv run prime doctor
```

Run tests and static checks:

```bash
uv run pytest -v
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
```

---

## Documentation

- [UI Architecture (Phase 03)](phase-03-reports/UI_ARCHITECTURE.md)
- [UI Setup Guide (Phase 03)](phase-03-reports/UI_SETUP_GUIDE.md)
- [UI Test Report (Phase 03)](phase-03-reports/UI_TEST_REPORT.md)
- [UI Performance Report (Phase 03)](phase-03-reports/UI_PERFORMANCE_REPORT.md)
- [Core Architecture Overview](docs/ARCHITECTURE.md)
- [Development Setup](docs/DEVELOPMENT_SETUP.md)
- [Security Model](docs/SECURITY.md)
- [Third-Party Notices & Attribution](THIRD_PARTY_NOTICES.md)
- [Changelog](CHANGELOG.md)

## License

Newly authored PRIME code is licensed under the [MIT License](LICENSE) (`Copyright (c) 2026 MrhRafi3`). PySide6/Qt6 is used dynamically under LGPLv3; foundational reference attribution for `VISION-1.2` (MIT) is preserved in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
