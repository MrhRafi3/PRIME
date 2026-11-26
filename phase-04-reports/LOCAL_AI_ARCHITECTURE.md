# PRIME Local AI Architecture (Phase 04)

## 1. Overview

PRIME executes 100% local LLM inference on macOS Apple Silicon via `mlx-lm` (`0.32.2`) and `mlx` (`0.32.5`) inside a layered, provider-agnostic module hierarchy under `src/prime/intelligence/`.

```
src/prime/intelligence/
├── prompts/
│   ├── system_prompt.md    # External Bangla/English/Banglish persona & safety rules
│   └── loader.py           # Loads prompt file & appends bounded memory notes
├── models/
│   └── registry.py         # ApprovedModelSpec catalog & offline models_dir validation
├── providers/
│   ├── base.py             # LLMProvider protocol, StreamChunk, ProviderStatus
│   └── mlx_provider.py     # Offline MLX-LM backend (streaming, cancel, cache clear)
├── generation/
│   └── service.py          # Memory budget checks & max_tokens/context enforcement
├── runtime/
│   └── manager.py          # LocalAIRuntime 8-state machine & telemetry tracking
├── context/
│   └── assembler.py        # Multi-turn history + FTS5 notes + external system prompt
└── memory/                 # Phase 02 SQLite + FTS5 local persistence
```

---

## 2. Key Architectural Behaviors

1. **Lazy Model Loading:** `PrimeApp.bootstrap()` initializes `ModelRegistry`, `MLXProvider`, and `LocalAIRuntime` in `Model Not Installed` or `Model Available` state without loading any weights into unified memory until the user clicks **Load Model** (or explicitly enables `auto_load_model`).
2. **UI Thread Isolation:** `InferenceWorker` (`src/prime/ui/bridge.py`) runs `load_local_model()` and `submit_text_message(..., on_token=...)` on a dedicated `QThread`, emitting queued `tokenDelta`, `generationFinished`, and `modelLoadFinished` signals to `PrimeUIBridge`.
3. **Eight-State Runtime Machine (`RuntimeState`):**
   `Model Not Installed` -> `Model Available` -> `Loading Model` -> `Ready` -> `Thinking` -> `Streaming Response` -> `Cancelling` -> `Error`.
4. **Explicit Unloading & Metal Cache Release:** Calling `unload_local_model()` drops model/tokenizer references, forces `gc.collect()`, and calls `mlx.core.clear_cache()`, returning Metal active memory to `0.0 MB`.
5. **Non-Thinking Chat Template Handling:** `MLXProvider._format_prompt()` attempts `apply_chat_template(..., enable_thinking=False)` for reasoning-capable tokenizers (such as `Qwen3`) and falls back seamlessly for standard `Qwen2.5` / `Llama` templates.
