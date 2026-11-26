# PRIME — Phase 05 Voice Performance & M1 8 GB Resource Report

**Target Machine:** Apple MacBook Air M1, 8 GB Unified Memory (`macOS 27.2.1`)  
**Voice + AI Co-Residency Test:** Concurrent loaded Whisper STT (`whisper.cpp` Metal) + MLX LLM (`qwen2.5-1.5b-4bit`) + macOS `AVSpeechSynthesizer` + 100% network block (`socket.create_connection` disabled)

---

## 1. Combined Memory & Pressure Results (STT + LLM + TTS)

| Configuration | Combined Load Time | Loaded Process RSS | MLX Active Mem | MLX Peak Mem | Process Peak RSS | Post-Unload RSS | Swap Delta | Post-Test System Mem Free |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`qwen2.5-1.5b-4bit` + `whisper-small-q5_1` + `AVSpeechTTS`** | `~1.0 s` | `275.45 MB` | `831.18 MB` | `974.96 MB` | `1,152.28 MB` | `183.75 MB` | `+219.8 MB` (`622.62M -> 842.44M`) | `42%` free |
| **`qwen2.5-1.5b-4bit` + `whisper-large-v3-turbo-q5_0` + `AVSpeechTTS`** | `1,176.3 ms` | `314.47 MB` | `831.18 MB` | `995.82 MB` | `1,075.27 MB` | `236.12 MB` | `+344.1 MB` (`622.62M -> 966.75M`) | `44%` free |

> **Note:** On Apple Silicon, `ps` process RSS excludes a portion of wired/GPU Metal allocations while `resource.getrusage(ru_maxrss)` and MLX `peak_memory_mb` reflect peak unified GPU + CPU allocations. Both combined configurations ran safely with **42%–44% system-wide memory free** and **zero OOM or thermal throttling**.

---

## 2. Multi-Turn End-to-End Voice Latency

### A. `whisper-small-q5_1` + `qwen2.5-1.5b-4bit` (3 Repeated Turns)
- **Turn 1 (English):** STT `587 ms` -> LLM `"I'm here to help with local issues..."` -> RSS `237.11 MB`
- **Turn 2 (Bangla input):** STT `12,867 ms` (English hallucination on `small-q5_1`) -> RSS `314.95 MB`
- **Turn 3 (English repeat):** STT `542 ms` -> LLM `"I'm PRIME, your local assistant..."` -> RSS `324.95 MB`

### B. `whisper-large-v3-turbo-q5_0` + `qwen2.5-1.5b-4bit` (English + Bangla Turns)
- **Turn 1 (English):** STT `2,439 ms` (`"Crime. Check system battery and memory status please."`) -> LLM `508.9 ms` (`"Understood. Checking system battery and memory status."`) -> AVSpeech TTS -> RSS `252.14 MB`
- **Turn 2 (Bangla, hint `"bn"`):** STT `2,700 ms` (`"হেলো প্রাইম তুমি কেমো নাছো"`) -> LLM `1,185.5 ms` -> AVSpeech (`Piya`) -> RSS `277.67 MB`

---

## 3. Responsiveness & Resource Discipline

- **UI Thread Isolation:** Whisper model load & transcription execute on `VoiceWorker` (`QThread`), MLX streaming executes on `InferenceWorker` (`QThread`), telemetry runs on `MetricsWorker` (`QThread`), and `AVSpeechSynthesizer` dispatches asynchronously via CoreAudio.
- **Explicit Memory Reclamation:** `VoiceCoordinator.unload_stt()` releases the `pywhispercpp` Metal context and triggers `gc.collect()` (dropping standalone `whisper-large-v3-turbo-q5_0` process RSS from `787.78 MB` back to `78.59 MB`). `PrimeApp.shutdown()` tears down TTS, Double-Clap monitor, audio capture, STT, and MLX in sequence.
- **Double-Clap CPU Overhead (When Opted In):** Processes 1024-sample `float32` buffers (15.625 callbacks/sec at 16 kHz) using only numpy vectorized RMS (`sqrt(mean(x^2))`), costing negligible CPU and `0` retained historical frames.
