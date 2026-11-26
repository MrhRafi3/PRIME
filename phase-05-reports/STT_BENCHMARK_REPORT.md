# PRIME — Phase 05 Offline STT Benchmark Report

**Hardware:** Apple Silicon MacBook Air M1 (8 GB Unified Memory), `macOS 27.2.1` (`arm64`)  
**Engine:** `pywhispercpp==1.5.1` (`whisper.cpp` with Apple Metal GPU + Flash Attention enabled, `n_threads=4`)  
**Network State:** `socket.create_connection` hard-blocked (100% offline verification)  
**Audio Source:** Offline synthesized 16 kHz mono float32 PCM arrays in RAM (deleted immediately after memory copy; zero microphone hardware touched)

---

## 1. Approved Local STT Models Verified on Disk

Stored under `~/Library/Application Support/PRIME/models/stt/`:

| Slug | File | Disk Size | SHA-256 | License |
| :--- | :--- | :---: | :--- | :--- |
| `whisper-small-q5_1` | `ggml-small-q5_1.bin` | `181.3 MiB` (`190,085,487` bytes) | `ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb` | MIT |
| `whisper-large-v3-turbo-q5_0` | `ggml-large-v3-turbo-q5_0.bin` | `547.4 MiB` (`574,041,195` bytes) | `394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2` | MIT |

---

## 2. Standalone Model Benchmarks

| Metric | `whisper-small-q5_1` | `whisper-large-v3-turbo-q5_0` |
| :--- | :---: | :---: |
| Model Load Time (`ms`) | `273.8 ms` | `277.0 ms` |
| Metal Static Buffer (`MTL0`) | `189.49 MB` | `573.40 MB` |
| RSS Before Load | `77.91 MB` | `128.11 MB` |
| RSS Loaded | `412.28 MB` | `787.78 MB` |
| RSS After Transcribe | `472.97 MB` | `647.83 MB` |
| RSS After `unload()` + `gc.collect()` | `127.89 MB` | `78.59 MB` |
| Swap Delta (`vm.swapusage`) | `0.00 MB` (`622.62M` unchanged) | `0.00 MB` (`622.62M` unchanged) |

---

## 3. Language-by-Language Transcription Accuracy & Speed

### A. English (`SpeechLanguage.ENGLISH`, hint `"en"`)
- **Prompt (`3.71 s`, Apple `Daniel`):** `"PRIME, check system battery and memory status please."`
- **`whisper-small-q5_1`:** `"Crime, check system battery and memory status please."` — **`591 ms`** (`RTF 0.159`). Fast (`< 0.6 s`), accurate words aside from proper noun `PRIME` -> `Crime` on synthetic voice.
- **`whisper-large-v3-turbo-q5_0`:** `"Crime. Check system battery and memory status please."` — **`2,247 ms`** (`RTF 0.606`). Clean punctuation and phrasing (`PRIME` -> `Crime` on un-prompted proper noun).

### B. Bangla (`SpeechLanguage.BANGLA`, hint `"bn"`)
- **Prompt (`2.30 s`, Apple `Piya`):** `"হ্যালো প্রাইম, তুমি কেমন আছো?"`
- **`whisper-small-q5_1`:** `"Looks good. Did you take a glass of hot water to get so hot in your body?"` — **`12,880 ms`** (`RTF 5.600`). **Failed / hallucinated English.** `small-q5_1` lacks sufficient Bengali decoder capacity and entered decoder repetition/fallback.
- **`whisper-large-v3-turbo-q5_0`:** `"হেলো প্রাইম তুমি কেমো নাছো"` — **`2,433 ms`** (`RTF 1.058`). **Accurate phonetic Bengali script transcription** in real-time-class latency (`2.43 s`).

### C. Bangla with Auto-Detection (`SpeechLanguage.AUTO_BN_EN`, hint `"auto"`)
- **Prompt (`1.95 s`, Apple `Piya`):** `"আমি বাংলায় কথা বলছি।"`
- **`whisper-small-q5_1`:** Detected `gu` (`p=0.26`), output garbled mixed script (`"ँ हूँँँ 없이 male kitty"`, `14,306 ms`, `RTF 7.336`).
- **`whisper-large-v3-turbo-q5_0`:** Auto-detected `hi` (`p=0.79`) and transliterated Bengali into Devanagari (`"आमी बालाज को था बोल ची?"`, `4,483 ms`, `RTF 2.299`).
- **Practical takeaway:** Short synthetic or `bn-IN`-prosody utterances can trigger `hi`/`gu` confusion in unhinted `auto` mode. Explicitly selecting **Bangla (`bn`)** mode resolves Bengali script cleanly on `large-v3-turbo-q5_0`.

### D. Banglish (Romanized Bengali Mixed with English, hint `"auto"`)
- **Prompt:** `"Ami bhalo achi, PRIME status check koro."`
- **With `Piya` (`bn-IN` voice, `3.35 s`):**
  - `whisper-small-q5_1`: `",,,, "` (`13,844 ms`, unusable).
  - `whisper-large-v3-turbo-q5_0`: Detected Hindi and emitted Devanagari phonetic words (`"आव मी बावलो आवची, प्राइम स्टेक आस चेक करो."`, `4,561 ms`). Notice phonetically it actually recognized `"ami bhalo achi, prime status check koro"`, rendered in Devanagari due to `hi` auto-detection.
- **With `Rishi` (`en-IN` voice, `2.96 s`):**
  - `whisper-small-q5_1`: `"I am Ibalo Achi, Prime status check Koro"` (`958 ms`, `RTF 0.324`).
  - `whisper-large-v3-turbo-q5_0`: `"Ami Balohachi, Prime Status Check Coro."` (`4,299 ms`, `RTF 1.452`).

---

## 4. Honest Assessment & M1 Recommendation

1. **English-only speed priority:** `whisper-small-q5_1` is ultra-fast (`0.16x` real-time, `~412 MB` RSS) and stays light on 8 GB RAM, but **must not be relied on for Bangla speech**.
2. **Bangla + English bilingual recommendation:** **`whisper-large-v3-turbo-q5_0`** is strongly recommended whenever Bangla is used. Because `large-v3-turbo` uses only 4 text decoder layers vs 12 in `small`, it runs Bangla faster (`2.43 s` vs `12.88 s`), preserves Bengali script cleanly with `"bn"`, and still fits within `~1.05 GB` peak process RSS alongside `Qwen2.5-1.5B-Instruct-4bit`.
3. **Banglish honesty:** Whisper has no native `"banglish"` Romanization token mode; pure Banglish without script hints splits unpredictably across Latin (`"Ami Balohachi..."`), Bengali, or Devanagari (`hi` auto-detect). Users get best reliability by speaking either Bengali (`bn`) or English (`en`), or switching Settings language mode accordingly.
