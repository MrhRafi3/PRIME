# PRIME Voice Model & Dependency License Audit (Phase 05)

**Audit Date:** 2026-11-26  
**Target Platform:** macOS Apple Silicon M1, 8 GB RAM (`Python 3.12.16`)  

---

## 1. Python Audio, STT & TTS Dependencies Evaluated

| Package | Resolved Version | License | Size / Footprint | Compatibility & Notes |
| :--- | :--- | :--- | :--- | :--- |
| **`sounddevice`** | `0.5.6` | **MIT** | Lightweight (`cffi`, bundles macOS arm64 PortAudio dylib in wheel) | Clean NumPy PCM capture; avoids `PyAudio` Homebrew header build issues. |
| **`pyobjc-framework-AVFoundation`** | `13.1` | **MIT** (PyObjC) + Apple OS Frameworks | Lightweight macOS system bridge (5 `pyobjc` packages) | Provides native `AVSpeechSynthesizer` (offline TTS) and `AVCaptureDevice` (Mic TCC status). |
| **`pywhispercpp`** *(Recommended STT)* | `1.5.1` | **MIT** (`whisper.cpp` + bindings) | **18 packages total** (zero `torch` / `numba` / `scipy`) | Runs `whisper.cpp` locally on macOS; compact quantized GGML models. |
| **`mlx-whisper`** *(Alternative STT)* | `0.4.3` | **MIT** | **45 packages** (pulls `torch==2.15.0`, `numba`, `llvmlite`, `scipy`, `sympy`) | Native MLX GPU execution, but adds heavy PyTorch/Numba wheel bloat. |

**License Compliance Note:** Zero GPL dependencies are introduced. All evaluated packages use **MIT** (compatible with PRIME's MIT license and `VISION-1.2` attribution). `Piper TTS` (GPLv3 engine + restricted voice datasets) and `edge-tts` (cloud + LGPLv3) remain explicitly excluded.

---

## 2. Offline STT Model Shortlist (M1 8 GB)

All Whisper GGML models below are hosted at `ggerganov/whisper.cpp` (converted from OpenAI Whisper under **MIT License**) and stored under `~/Library/Application Support/PRIME/models/stt/`:

| Model File | Source Repository | License | Download / Disk Size | Est. Peak RAM | Bangla + English Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ggml-small-q5_1.bin`** | `ggerganov/whisper.cpp` | **MIT** | **~181 MiB** | ~400–600 MB | Fast baseline; handles English well and basic Bangla phrases, easily coexists with `qwen2.5-1.5b-4bit` (`1.24 GB`) on 8 GB M1. |
| **`ggml-large-v3-turbo-q5_0.bin`** | `ggerganov/whisper.cpp` | **MIT** | **~547 MiB** | ~900–1,250 MB | Substantially higher Bangla & Banglish accuracy; still fits 8 GB M1 alongside `qwen2.5-1.5b-4bit` (`~2.5 GB` combined AI+STT) or with sequential unload. |
| *(`ggml-base.bin` fallback)* | `ggerganov/whisper.cpp` | **MIT** | ~142 MiB | ~250–350 MB | Too weak on Bangla script accuracy compared to `small-q5_1` and `large-v3-turbo-q5_0`. |

---

## 3. Offline TTS Evaluation

| Engine | Offline? | Bangla Voice Availability | English Quality | License & Size |
| :--- | :--- | :--- | :--- | :--- |
| **macOS `AVSpeechSynthesizer` (`AVFoundation`)** *(Recommended)* | **100% Offline** | **Yes (`Piya` `bn_IN` verified installed via `say -v '?'`)** | **Good** (`Daniel` `en_GB`, `Samantha` `en_US`, `Rishi`/`Aman` `en_IN`) | **0 MB download**, **~0 MB extra RAM**, Apple system framework via MIT `pyobjc`. Mechanical cadence on complex Bangla conjuncts (to be tested honestly). |
| **Kokoro-82M** | Offline | **No** (upstream lacks Bangla weights; relies on OS/cloud fallback for Bengali) | Excellent neural English | Apache-2.0 (`~350 MB` RAM), excluded as primary because it lacks native Bangla. |
| **Piper TTS** | Offline | Limited / dataset-dependent | Good | **GPLv3 engine** + non-commercial voice restrictions — excluded for license compliance. |
