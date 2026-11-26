# PRIME — Phase 05 Voice Privacy & Security Audit

**Audit Scope:** `src/prime/voice/`, `src/prime/core/app.py`, `src/prime/config/settings.py`, `src/prime/ui/bridge.py`, `src/prime/ui/qml/`, `src/prime/system/macos/controller.py`  
**Audit Date:** 2026-11-26

---

## 1. Privacy & Security Guarantees Verified

| Requirement | Implementation & Verification | Status |
| :--- | :--- | :---: |
| **100% Local STT & TTS** | `WhisperCppSTTProvider` enforces `HF_HUB_OFFLINE=1` and runs strictly on in-memory `np.ndarray`; `AVSpeechTTSProvider` calls macOS `AVFAudio` directly. Verified with `socket.create_connection` monkeypatched/blocked in unit tests (`test_voice.py`) and live benchmarks. | **PASS** |
| **Zero Raw Audio Disk Persistence** | `AudioCaptureSession` buffers 16 kHz `float32` chunks strictly in RAM (`max_duration_s=30.0` cap), copies into `np.ndarray` on `stop_and_consume()`, fills every chunk with `0.0`, and clears `_chunks`. `VoiceCoordinator.stop_and_transcribe()` also zero-fills the working sample array in `finally:`. Zero temporary `.wav`/`.pcm` files are written anywhere. | **PASS** |
| **Double-Clap Disabled by Default** | `ActivationConfig.double_clap_enabled = False`, `VoiceCoordinator(..., double_clap_enabled=False)`. Attempting `set_double_clap_monitoring(True)` while opted out raises `VoicePipelineError`. Disabling `double_clap_enabled` in Settings stops the monitor stream immediately. | **PASS** |
| **No Wake-Word / No Silent Mic Capture** | `wake_word_enabled = False` and `background_mic_enabled = False` remain locked/enforced by config validation (`test_invalid_or_unsafe_config_rejected`). | **PASS** |
| **Non-Prompting TCC Microphone Check** | `check_microphone_permission()` uses `AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)` passively. `test_macos_controller_does_not_prompt_hardware_tcc` verifies zero prompt invocations during checks; `start_voice_recording(allow_prompt=False)` raises `PermissionDeniedError` unless `GRANTED`. | **PASS** |
| **STT Model Allowlist & SHA-256** | `STTModelRegistry` restricts weights to `APPROVED_STT_MODELS`, blocks path traversal (`../`, symlinks escaping `stt_models_dir`), and validates SHA-256 digests (`test_stt_registry_approval_checksum_and_path_traversal`). | **PASS** |
| **Zero Private Audio / Transcript Leakage in Logs** | Structured logs record only metadata (`stt_model`, `has_text`, `duration_ms`); raw speech transcripts or audio bytes are never logged when `log_private_content=False`. | **PASS** |
| **CoreAudio Contention Safety** | `VoiceCoordinator.start_recording()` automatically stops active TTS playback (barge-in) and pauses `DoubleClapMonitor` before starting `AudioCaptureSession`. | **PASS** |

---

## 2. Dependency License Compliance

- `sounddevice==0.5.6`: MIT (`PortAudio` MIT-style).
- `pywhispercpp==1.5.1` + `ggml-*.bin`: MIT.
- `pyobjc-framework-AVFoundation==13.1`: MIT (system `AVFoundation` / `AVFAudio` frameworks).
- Zero GPLv3 packages added to `PRIME` (`pyproject.toml` / `uv.lock` verified).

---

## 3. Repository Hygiene Verification

- Model weights (`*.bin`, `*.safetensors`) and local user audio/databases/logs live strictly outside Git under `~/Library/Application Support/PRIME/` and `.gitignore`.
- No microphone hardware, camera, or TCC prompts are invoked automatically on app startup or during `uv run pytest`.
