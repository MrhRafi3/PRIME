# PRIME Model Benchmark Report (Apple M1, 8 GB Unified Memory)

**Host Hardware:** Apple MacBook Air M1, 8 GB Unified Memory (`8,589,934,592` bytes), macOS `27.2.1` (`arm64`)  
**Runtime:** `mlx==0.32.5`, `mlx-lm==0.32.2`, `mlx-metal==0.32.5`, Python `3.12.16`  
**Methodology:** Each approved model was downloaded one at a time into `~/Library/Application Support/PRIME/models/`, verified for repository SHA, `config.json`, tokenizer files, and Apache 2.0 license, then benchmarked offline (`socket.create_connection` & `socket.socket.connect` blocked) in isolation with `unload()` + Metal cache release before loading the next model.

---

## 1. Approved Models Tested

| Model | Repository | Verified SHA | License | Disk Size |
| :--- | :--- | :--- | :--- | :--- |
| **Qwen 2.5 1.5B Instruct (4-bit MLX)** | `mlx-community/Qwen2.5-1.5B-Instruct-4bit` | `8b403126fc14f14cfc99bb4cfa72ecbc129ea677` | `apache-2.0` | **~840 MB** (`828M` safetensors) |
| **Qwen 3 1.7B (4-bit MLX)** | `mlx-community/Qwen3-1.7B-4bit` | `3b1b1768f8f8cf8351c712464f906e86c2b8269e` | `apache-2.0` | **~940 MB** (`923M` safetensors) |

---

## 2. Quantitative Benchmark Results

| Metric | `qwen2.5-1.5b-4bit` | `qwen3-1.7b-4bit` (default template) | `qwen3-1.7b-4bit` (`enable_thinking=False`) |
| :--- | :--- | :--- | :--- |
| **Load Time** | **0.628 s** | **0.640 s** | ~0.64 s |
| **English Speed** | **52.32 tok/s** (`24` tok) | **45.95 tok/s** (`43` tok) | **45.96 tok/s** (`38` tok) |
| **Bangla Speed** | **50.55 tok/s** (`140` tok) | **44.36 tok/s** (`220` tok) | **44.92 tok/s** (`147` tok) |
| **Banglish Speed** | **52.51 tok/s** (`31` tok) | **45.20 tok/s** (`184` tok) | **45.98 tok/s** (`43` tok) |
| **MLX Active Memory** | **831.18 MB** | **923.17 MB** | **923.17 MB** |
| **MLX Peak Memory** | **1,243.98 MB** | **1,381.08 MB** | **~1,381 MB** |
| **Process Max RSS** | **801.23 MB** | **834.91 MB** | — |
| **Post-Unload MLX Active** | **0.0 MB** | **0.0 MB** | **0.0 MB** |
| **macOS Swap Delta** | **0.00 MB** (`537.69M -> 537.69M`) | **+65.31 MB** (`537.69M -> 603.00M`) | — |
| **Cancellation Check** | Stopped cleanly at 5 tokens | Stopped cleanly at 5 tokens | — |

---

## 3. Response Quality & Language Evaluation (Honest Assessment)

### `qwen2.5-1.5b-4bit`
- **English:** Crisp, coherent, fast (`52.3 tok/s`), follows concise instruction boundaries well (e.g., live UI run: *"Apple Silicon unified memory is a type of memory architecture that combines DRAM and SRAM to provide high-speed access to data."*, though note slight factual imprecision vs HBM/unified DRAM—typical for 1.5B).
- **Bangla:** Produces valid Bengali script fluently at `~50 tok/s`, but exhibits typical 1.5B limitations on open-ended prompts (occasional lexical inaccuracy/drift, e.g., *"আপ সিঙ্গ অফলাইন কাজ করি নাই, আমি অফলাইন কাজ করি"* or repetitive lists if `max_tokens` is high).
- **Banglish:** Understands Romanized Bangla prompts accurately and answers reliably in English (`31` tokens, `1.14s`).

### `qwen3-1.7b-4bit`
- **Default Template Finding:** Without `enable_thinking=False`, `Qwen3-1.7B-4bit` spends `140–220` tokens inside `<think>...</think>` blocks, frequently exhausting `max_tokens` on Bangla prompts before emitting the user-facing answer.
- **With `enable_thinking=False` (implemented in `MLXProvider`):**
  - **English:** Clean 2-sentence explanation at `45.96 tok/s`.
  - **Bangla:** Produces fluent Bengali script (`44.92 tok/s`), though repetitive phrasing occurred (*"সহায়তা করে তার জীবনে সহায়তা করে"*).
  - **Banglish:** Understood prompt intent, though mixed Hindi particles (`"ko"`, `"hai"`) appeared in Romanized output (*"Amar MacBook Air M1 8GB RAM ko bhalo bolbo"*).

---

## 4. Recommendation for M1 8 GB

- **Default Selected Model (`qwen2.5-1.5b-4bit`):** Best overall speed (`~50–52 tok/s`), lowest peak MLX memory (`1,244 MB`), zero macOS swap growth during active desktop use, and zero `<think>` overhead.
- **Secondary Installed Option (`qwen3-1.7b-4bit`):** Selectable in PRIME Settings (`Local MLX Model`) for users experimenting with Qwen 3 (`enable_thinking=False` enabled automatically).
- **Known Limitation:** Both `1.5B` and `1.7B` 4-bit models show minor factual/grammatical drift in Bangla compared to larger `3B–7B` models. Larger models were intentionally excluded in this Phase 04 benchmark per user directive.
