# Third-Party Notices & Attribution

This document distinguishes newly authored PRIME components, foundational inspiration/reference notices from `VISION-1.2`, and third-party packages.

---

## 1. Newly Authored PRIME Components

All modules under `src/prime/`, `tests/`, `scripts/`, and `docs/` in this repository were newly authored for **PRIME** (`com.mrhrafi3.prime`) and are licensed under the MIT License (`Copyright (c) 2026 MrhRafi3`). See [LICENSE](LICENSE).

---

## 2. Original `VISION-1.2` Foundational Attribution

PRIME was initiated following a technical audit of [`shaikhtaha258-maker/VISION-1.2`](https://github.com/shaikhtaha258-maker/VISION-1.2). While PRIME uses a clean-room modular architecture in Phase 02 without copying `VISION-1.2` source files verbatim, the original project's MIT copyright and permission notice is preserved below for foundational reference and any future geometry/concept continuity:

```text
MIT License

Copyright (c) 2026 Vision Assistant contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 3. Third-Party Packages

### Runtime Dependencies (Phases 03, 04 & 05)
- **PySide6-Essentials** (`6.10.3`) & **shiboken6** (`6.10.3`) — **GNU Lesser General Public License v3 (LGPLv3)** (`Copyright (C) The Qt Company Ltd.`). Used via dynamic linking; distributed bundles must preserve LGPLv3 notices and allow end-users to replace Qt shared libraries.
- **mlx** (`0.32.5`), **mlx-lm** (`0.32.2`), **mlx-metal** (`0.32.5`) — **MIT License** (`Copyright (c) Apple Inc.`).
- **pywhispercpp** (`1.5.1`) & bundled `whisper.cpp` Metal/CPU runtime — **MIT License** (`Copyright (c) 2023-2026 A.B. / Georgi Gerganov & whisper.cpp contributors`).
- **sounddevice** (`0.5.6`) — **MIT License** (`Copyright (c) 2015-2025 Matthias Geier`), wrapping bundled **PortAudio** (`V19.7.0-devel`, **MIT-style permissive license**).
- **pyobjc-framework-AVFoundation** (`13.1`, pulling `pyobjc-core`, `pyobjc-framework-Cocoa`, `pyobjc-framework-CoreAudio`, `pyobjc-framework-Quartz`) — **MIT License** (`Copyright (c) 2002-2026 Ronald Oussoren and contributors`), bridging Apple macOS `AVFoundation` (`AVCaptureDevice`) and `AVFAudio` (`AVSpeechSynthesizer`) system frameworks.
- **huggingface-hub** (`2.4.0`), **transformers** (`5.24.1`), **tokenizers** (`0.23.3`), **safetensors** (`0.8.0`), **sentencepiece** (`0.2.3`) — **Apache License 2.0**.
- **numpy** (`2.5.5`), **pydantic** (`2.14.4`), **jinja2** (`3.1.6`), **pyyaml** (`6.0.4`), **typer** (`0.29.2`), **rich** (`15.0.0`), **httpx** / **anyio** / **click** — **MIT / BSD-3-Clause** permissive licenses.

### Development & Verification Dependencies
- **pytest** (`>=8.3.0,<9.0.0`) — MIT License (`Copyright (c) 2004 Holger Krekel and others`)
- **ruff** (`>=0.8.0,<1.0.0`) — MIT License (`Copyright (c) 2022 Charles Marsh`)

---

## 4. Planned Future License Obligations (Phase 04+)

When UI and AI dependencies are introduced in later phases, the following compliance requirements apply:
- **PySide6 / Qt 6 (LGPLv3):** Must remain dynamically linked when distributed; packaged `.app` bundles must include the LGPLv3 notice and allow users to swap Qt shared libraries.
- **Avoid GPLv3 linking:** Avoid bundling GPLv3 libraries (such as Piper's core engine or linked `espeak-ng`) into the MIT-licensed PRIME core.
- **Model Weights:** Downloaded local model weights (LLM, Whisper, TTS, MediaPipe) must remain separate from the source repository and display their upstream model licenses.
