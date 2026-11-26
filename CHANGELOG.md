# Changelog

All notable changes to PRIME will be documented in this file.

## [0.3.0-phase04] - 2026-11-26 (Phase 04 — Local AI Intelligence Engine)

### Added
- `mlx-lm` (`0.32.2`) / `mlx` (`0.32.5`) Apple Silicon local inference engine (`MLXProvider`) with `HF_HUB_OFFLINE=1` enforcement, token streaming, cancellation, and explicit Metal cache unloading.
- Approved local model catalog & sandboxed directory validator (`prime.intelligence.models.ModelRegistry`).
- External configurable Bangla/English/Banglish system prompt (`src/prime/intelligence/prompts/system_prompt.md`).
- Memory-budgeted `GenerationService` and 8-state `LocalAIRuntime` (`Model Not Installed` through `Error`).
- Background `InferenceWorker` in `PrimeUIBridge`, live token streaming in `Main.qml`, `Load Model` / `Unload` / `Stop` controls, `tok/s` & token telemetry, and model selection in `SettingsDialog.qml`.
- Offline intelligence unit/integration tests (`tests/unit/test_intelligence_engine.py`), benchmark script (`scripts/benchmark_models.py`), and Phase 04 reports & screenshots (`phase-04-reports/`).

## [0.2.0-phase03] - 2026-11-26 (Phase 03 — JARVIS Desktop UI)

### Added
- PySide6 (`PySide6-Essentials 6.10.3`) Qt Quick/QML JARVIS desktop interface (`src/prime/ui/`).
- `PrimeUIBridge`, `MessageListModel`, and background `QThread` `MetricsWorker` keeping all OS telemetry off the UI thread.
- Six-region HUD (`Main.qml`, `JarvisHud.qml`, `SettingsDialog.qml`): Header, animated central HUD, Conversation panel with truthful offline notice, Activation controls (Push-to-Talk UI state + Double-Clap config), System Telemetry (CPU, Unified Memory, Battery), and Local-Only Footer.
- `MacOSSystemController.get_system_metrics()` (`ps`, `sysctl`, `vm_stat`, `pmset`) with graceful `None` fallbacks.
- `save_config_toml()` atomic `0700`/`0600` persistence and `prime ui` CLI launch command.
- UI integration tests (`tests/ui/test_ui_bridge.py`), metrics/persistence unit tests (`tests/unit/test_metrics.py`), and Phase 03 reports (`phase-03-reports/`).

## [0.1.0] - 2026-11-26 (Phase 02 — Core Foundation)

### Added
- Independent Python 3.12 (`arm64`) project layout managed with `uv` (`pyproject.toml`, `uv.lock`).
- Centralized typed configuration (`prime.config`) with TOML/JSON support and `PRIME_*` environment overrides.
- Secure rotating local logger (`prime.logging`) with automatic token/secret redaction and private-content suppression.
- Three-tier `SecurityManager` (`prime.security`) enforcing Tier 0/1/2 rules, sandbox path traversal guards, URL validation, and app allowlists.
- Platform Abstraction Layer (`prime.system.base.SystemController`) and `MacOSSystemController` (`prime.system.macos`).
- Local SQLite + FTS5 persistent memory foundation (`prime.intelligence.memory`) with versioned migrations and parameterized CRUD.
- Multi-turn `ContextAssembler` and typed contracts for future local LLM providers, offline voice (push-to-talk / double-clap, Bangla + English), on-demand vision, and capability-gated plugins.
- Unit, integration, and security test suites (`tests/`) plus `README.md`, `docs/`, `LICENSE`, and `THIRD_PARTY_NOTICES.md`.
