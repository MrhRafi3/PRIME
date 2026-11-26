# PRIME Local AI Performance Report (M1 8 GB Unified Memory)

**Host:** MacBook Air M1 (`8.0 GB` unified memory, passive fanless cooling), macOS `27.2.1` (`arm64`)  
**Date:** 2026-11-26  

---

## 1. Observed Runtime & Memory Telemetry

| Measurement | Value | Notes |
| :--- | :--- | :--- |
| **Idle UI + Core (No Model Loaded)** | **~196.6 MiB RSS** (`0` swaps) | Lazy model loading keeps startup RAM minimal |
| **`qwen2.5-1.5b-4bit` Active MLX / Peak MLX** | **831.2 MB / 1,244.0 MB** | `801.2 MB` process RSS; `0.00 MB` swap delta |
| **`qwen3-1.7b-4bit` Active MLX / Peak MLX** | **923.2 MB / 1,381.1 MB** | `834.9 MB` process RSS; `+65.3 MB` swap delta |
| **Live UI + Loaded `qwen2.5-1.5b-4bit` Total System Memory** | **6.20 / 8.0 GB (78%)** | Observed in live `Main.qml` telemetry while desktop apps open; `17.7%` CPU |
| **Post-Unload MLX Active Memory** | **0.0 MB** | Verified deterministic release via `unload()` + `mx.clear_cache()` |
| **Token Throughput (`qwen2.5-1.5b-4bit`)** | **48.4 – 52.5 tok/s** | `0.63 s` cold load; responsive real-time UI streaming |
| **Token Throughput (`qwen3-1.7b-4bit`)** | **44.4 – 46.0 tok/s** | `0.64 s` cold load |

---

## 2. Safety Mechanisms for 8 GB M1

1. **Lazy Loading by Default:** `auto_load_model = False` ensures PRIME does not consume ~1 GB of unified memory until requested.
2. **Memory Budget Gate (`GenerationService.check_memory_budget`):** Blocks loading any model whose `estimated_ram_mb` exceeds the profile's `memory_budget_mb` (`2200 MB` Eco, `3200 MB` Balanced).
3. **Bounded Context & Token Caps:** Default `max_context_tokens = 4096` (Eco `2048` / Balanced `4096`), `ContextAssembler` char budget `8000`, and `max_generation_tokens = 512` prevent unbounded KV-cache growth.
4. **Sequential Isolation:** Only one model can reside in `MLXProvider` at a time (`load()` invokes `unload()` before loading new weights).
