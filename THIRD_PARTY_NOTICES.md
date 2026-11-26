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

## 3. Third-Party Packages (Phase 02)

### Runtime Dependencies
- **None.** Phase 02 core infrastructure depends strictly on the Python 3.12 standard library (PSF License v2).

### Development & Verification Dependencies
- **pytest** (`>=8.3.0,<9.0.0`) — MIT License (`Copyright (c) 2004 Holger Krekel and others`)
- **ruff** (`>=0.8.0,<1.0.0`) — MIT License (`Copyright (c) 2022 Charles Marsh`)

---

## 4. Planned Future License Obligations (Phase 03+)

When UI and AI dependencies are introduced in later phases, the following compliance requirements apply:
- **PySide6 / Qt 6 (LGPLv3):** Must remain dynamically linked when distributed; packaged `.app` bundles must include the LGPLv3 notice and allow users to swap Qt shared libraries.
- **Avoid GPLv3 linking:** Avoid bundling GPLv3 libraries (such as Piper's core engine or linked `espeak-ng`) into the MIT-licensed PRIME core.
- **Model Weights:** Downloaded local model weights (LLM, Whisper, TTS, MediaPipe) must remain separate from the source repository and display their upstream model licenses.
