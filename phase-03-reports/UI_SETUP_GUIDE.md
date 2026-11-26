# PRIME UI Setup & Launch Guide (Phase 03)

## Prerequisites

- macOS on Apple Silicon (verified on M1 8 GB RAM, macOS `27.2.1`)
- `uv` (`>=0.13`)
- Python `3.12` (`arm64` managed automatically by `uv`)

## Installation

From the `PRIME/` repository root:

```bash
uv sync --python 3.12 --group dev
```

This installs only `PySide6-Essentials` (`6.10.3`) and `shiboken6` (`6.10.3`) for the runtime UI, plus `pytest` and `ruff` for development. No AI runtimes or models are downloaded.

## Launching the Desktop UI

```bash
uv run prime ui
```

Optional flags for automated smoke testing and screenshots:

```bash
uv run prime ui --auto-close-ms 2500 --screenshot-path phase-03-reports/screenshots/prime_main_hud.png
```

## Available UI Controls (Phase 03 Scope)

- **Push-to-Talk (UI State):** Toggles assistant state between `IDLE` and `LISTENING` in the HUD without accessing the microphone.
- **Conversation Input:** Enter text and press `Return` or click `Send`. Messages are saved locally to SQLite (`~/Library/Application Support/PRIME/prime_memory.db`), and PRIME clearly displays an unavailable notice because the AI engine is not connected yet.
- **Settings:** Configure Double-Clap activation preference, Language Priority (`bn-en` vs `en`), and M1 8 GB Memory Profile (`eco`, `balanced`, `heavy`). Settings persist to `~/Library/Application Support/PRIME/config.toml` with `0600` permissions.

## Deferred Features (Phase 04+)

- Local LLM inference (`mlx-lm` / `llama.cpp`)
- Microphone capture, offline STT (`mlx-whisper`), offline TTS (`Kokoro` / `AVSpeechSynthesizer`), and real double-clap detection
- On-demand camera & hand tracking
