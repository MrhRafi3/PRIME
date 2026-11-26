# PRIME — Phase 04 Implementation Plan (Local AI Intelligence Engine)

**Product:** PRIME (`com.mrhrafi3.prime`)  
**Baseline Commit:** `3587c8cc8032a84814e983a57953b0f9007b9f77` (`main`)  
**Target Hardware:** Apple Silicon MacBook Air M1, 8 GB Unified Memory (`118 GiB` free disk)  
**Runtime Environment:** Python `3.12.16` (`arm64`), `PySide6-Essentials 6.10.3`  
**Date:** 2026-11-26  

---

## 1. Pre-Implementation Audit Summary

- **Git State:** Clean working tree on `main` at `3587c8cc8032a84814e983a57953b0f9007b9f77`.
- **MLX / MLX-LM Compatibility:** Dry-run `uv pip compile --python 3.12` resolved `mlx==0.32.5`, `mlx-lm==0.32.2`, and `mlx-metal==0.32.5` cleanly for `macosx_arm64` Python 3.12. All transitive dependencies (`mlx`, `mlx-lm`, `huggingface-hub`, `transformers`, `tokenizers`, `safetensors`, `sentencepiece`, `pydantic`, `jinja2`, `numpy`) use permissive licenses (MIT / Apache 2.0 / BSD).
- **8 GB M1 Memory Budget:** Phase 03 UI peak RSS is **~196.6 MiB** (`0` swaps), and baseline macOS + desktop consumes ~5.0–5.5 GB during active multitasking. Keeping active 4-bit model weights in the **1.0–2.0 GB** range (`1.5B–3B` 4-bit MLX) with `max_context_tokens <= 4096` and lazy load / explicit unload preserves stability without SSD swap thrashing.

---

## 2. Proposed Architecture (`src/prime/intelligence/`)

1. **`providers/` (`base.py`, `mlx_provider.py`):**
   - Extends `LLMProvider` contract with: `initialize()`, `is_model_available()`, `load()`, `unload()`, `stream_generate()`, `cancel()`, `status()`, `memory_report()`.
   - Implements `MLXProvider` using `mlx-lm` with lazy imports, thread-safe cancellation (`threading.Event`), token streaming, and explicit Metal cache cleanup (`mx.clear_cache()` / `mx.metal.clear_cache()` + `gc.collect()`) on `unload()`.
2. **`models/` (`registry.py`):**
   - Curated local-only model registry (`ApprovedModelSpec`) with local directory discovery under `~/Library/Application Support/PRIME/models/<model_slug>/`.
   - Strict path validation (`Path.resolve().is_relative_to(models_dir)`), offline `local_files_only=True` loading during inference, and zero automatic remote downloads.
3. **`prompts/` (`system_prompt.md`, `loader.py`):**
   - Keeps PRIME's configurable Bangla + English + Banglish system prompt cleanly separated in `system_prompt.md` rather than hardcoded inside Python business logic.
4. **`generation/` (`service.py`):**
   - `GenerationService` enforcing memory budget checks, context token caps, `max_tokens` limits, streaming callbacks, cancellation, and clean error states.
5. **`runtime/` (`manager.py`):**
   - `LocalAIRuntime` lifecycle manager tracking `RuntimeStatus` (`MODEL_NOT_INSTALLED`, `MODEL_AVAILABLE`, `LOADING_MODEL`, `READY`, `THINKING`, `STREAMING`, `CANCELLING`, `ERROR`), active model ID, tok/s telemetry, and memory usage.
6. **`context/` (`assembler.py`):**
   - Connects `system_prompt.md`, recalled SQLite FTS5 notes, and bounded multi-turn conversation history.

---

## 3. UI & Core Integration

- **`PrimeApp` (`prime/core/app.py`):**
  - Lazily attaches `LocalAIRuntime` (no automatic model load at startup unless explicitly enabled in config).
  - Updates `submit_text_message()` / `submit_text_message_async()` to stream tokens into the UI, persist completed assistant replies in SQLite `MemoryStore`, and support `cancel_generation()`.
  - Never fabricates answers when `MODEL_NOT_INSTALLED` or `ERROR`.
- **`PrimeUIBridge` & QML (`prime/ui/`):**
  - Runs model load and streaming generation on a dedicated `QThread` worker (`InferenceWorker`), never blocking the UI thread.
  - Exposes new runtime states (`Model Not Installed`, `Model Available`, `Loading Model`, `Ready`, `Thinking`, `Streaming Response`, `Cancelling`, `Error`), active model selector, Load/Unload & Stop/Cancel controls, approximate tok/s, and generated token count.
  - Keeps `AI ENGINE: NOT CONNECTED` / `Model Not Installed` visible until a model is genuinely loaded and ready.

---

## 4. Model Candidate Shortlist & Download Gate

Before downloading any weights, explicit user approval will be requested for one or two benchmark candidates from this M1 8 GB shortlist:

1. **`mlx-community/Qwen2.5-1.5B-Instruct-4bit`** (~0.9 GB download, Apache 2.0, ~1.2–1.5 GB RAM) — fast baseline for Bangla + English.
2. **`mlx-community/Qwen3-1.7B-4bit`** (~1.1–1.2 GB download, Apache 2.0, ~1.4–1.8 GB RAM) — modern compact multilingual reasoning + Bangla/English.
3. **`mlx-community/Qwen2.5-3B-Instruct-4bit`** (~1.7–1.8 GB download, Apache 2.0, ~2.2–2.7 GB RAM) — stronger Bangla fluency & instruction following while still fitting 8 GB unified memory.

*(No model weights will be downloaded until the user explicitly approves.)*

---

## 5. Verification Plan

1. **Automated Tests (Mocked `LLMProvider`):** Contract tests, load/unload, streaming tokens, cancellation, OOM/error handling, Bangla/English/Banglish context assembly, no-model-installed honesty check, UI bridge state transitions, memory budget guards.
2. **Offline & Security Audit:** Confirm zero cloud endpoints, `local_files_only=True` during inference, approved local model path enforcement, and private prompt redaction in logs.
3. **Live Model Benchmarks (Post-Approval Only):** Measure load time, peak RSS, tok/s, English/Bangla/Banglish quality, cancellation, and unload memory release on this M1 MacBook Air.
