# PRIME — Phase 05 Voice Setup & Usage Guide

**Target Platform:** macOS (Apple Silicon M1+, `arm64`), Python `3.12` via `uv`

---

## 1. Local Dependencies

Phase 05 dependencies are declared in `pyproject.toml` and pinned in `uv.lock`:
- `sounddevice==0.5.6`
- `pyobjc-framework-AVFoundation==13.1`
- `pywhispercpp==1.5.1`

Sync environment:
```bash
uv sync --python 3.12 --group dev
```

---

## 2. Local STT Model Placement (Zero Auto-Downloads)

PRIME never downloads model weights automatically at runtime. Place verified GGML Whisper models under:

```text
~/Library/Application Support/PRIME/models/stt/
├── ggml-small-q5_1.bin               # 181.3 MiB — fast English / light RAM
└── ggml-large-v3-turbo-q5_0.bin      # 547.4 MiB — best Bangla + English accuracy
```

Override directory if needed with `PRIME_STT_MODELS_DIR`.

Check installed SHA-256 digests:
```bash
shasum -a 256 ~/Library/Application\ Support/PRIME/models/stt/*.bin
```

Expected hashes:
- `ggml-small-q5_1.bin`: `ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb`
- `ggml-large-v3-turbo-q5_0.bin`: `394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2`

---

## 3. Offline macOS Voices Check

Verify built-in offline voices:
```bash
say -v '?' | grep -E "Piya|Daniel|Samantha"
```

If `Piya` (`bn_IN`) is missing on another Mac, download it once in **macOS System Settings -> Accessibility -> Spoken Content -> System Voice -> Manage Voices -> Bengali (India)**.

---

## 4. Using Voice Mode in PRIME HUD

Launch the desktop HUD:
```bash
uv run prime ui
```

1. **Microphone Permission:** On first voice click, macOS prompts once for Microphone access (or click **Grant Mic** if needed). PRIME never triggers this prompt at startup.
2. **Push-to-Talk:** Hold **Hold to Talk** or press the **Ctrl+Space** shortcut to capture audio locally in RAM; release to transcribe offline with Whisper and send to the loaded MLX LLM. Click **Cancel Voice** at any time to scrub buffers immediately.
3. **Select STT Model & Language:** Open **Settings** to choose `whisper-small-q5_1` (fast English) or `whisper-large-v3-turbo-q5_0` (recommended for Bangla + English), toggle **Offline TTS**, pick English voice (`Daniel`, `Samantha`, `Rishi`), and adjust Speech Rate/Volume.
4. **Opt-In Double-Clap (Optional):** Disabled by default. Enable **Double-Clap Activation (Opt-In)** in **Settings**, save, and click **Monitor** in `VOICE & ACTIVATION` to start/stop transient clap detection (zero audio saved).

---

## 5. Offline Verification Commands

```bash
uv run pytest -v
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run prime doctor
```
