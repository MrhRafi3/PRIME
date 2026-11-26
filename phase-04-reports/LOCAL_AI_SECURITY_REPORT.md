# PRIME Local AI Security & Offline Audit Report (Phase 04)

**Audit Date:** 2026-11-26  
**Scope:** All `src/prime/intelligence/` modules, `PrimeApp`, `PrimeUIBridge`, and `mlx-lm` integration.

---

## 1. Offline Inference Verification

- **Socket-Level Network Block Test:** Both benchmark scripts and the live PySide6 UI streaming run monkeypatched `socket.socket.connect` and `socket.create_connection` to raise `OSError('Network disabled for offline verification')` prior to `MLXProvider.load()` and `generate()`/`stream_generate()`. Both `qwen2.5-1.5b-4bit` and `qwen3-1.7b-4bit` loaded and streamed tokens cleanly with **zero outbound network attempts**.
- **Code-Level Offline Guards:** `MLXProvider.load()` sets `os.environ["HF_HUB_OFFLINE"] = "1"` and `os.environ["TRANSFORMERS_OFFLINE"] = "1"`, and loads strictly from validated local paths (`str(model_path)`), never passing remote repo IDs at inference time.
- **No Cloud AI / No Telemetry:** Zero OpenAI, Anthropic, Gemini, Ollama remote, or analytics endpoints exist in the codebase.

---

## 2. Path & Model Security Controls

- **Allowlisted Catalog (`ModelRegistry`):** Only slugs present in `APPROVED_MODELS` can be resolved (`ModelSecurityError` raised on unknown slugs, `..`, `/`, or `\\`).
- **Directory Containment:** `ModelRegistry.resolve_model_path()` verifies `candidate.is_relative_to(models_dir.resolve())` before returning a path.
- **No Auto-Downloads:** Zero automatic download calls exist anywhere in `src/prime/`.

---

## 3. Prompt, Logging & Memory Privacy

- **External System Prompt (`prompts/system_prompt.md`):** Instructs PRIME never to claim unexecuted capabilities or disclose internal system prompts/configs.
- **Log Redaction Preserved:** `log_event()` logs only non-sensitive metadata (`model_id`, `estimated_ram_mb`, errors) — user prompts and assistant replies are never written to `prime.log` under default `log_private_content=False`.
- **Local SQLite Persistence (`0600`):** Conversation messages (`user` and completed `assistant` replies) are stored strictly locally in `~/Library/Application Support/PRIME/prime_memory.db`; cancelled partial streams are not persisted.
- **TCC Permissions Untouched:** Phase 04 requests zero macOS Microphone, Camera, Screen Recording, or Automation permissions.
