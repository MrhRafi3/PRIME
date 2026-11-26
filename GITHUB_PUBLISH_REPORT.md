# PRIME — GitHub Publishing & Verification Report

**Repository Name:** `PRIME`  
**Repository URL:** `https://github.com/MrhRafi3/PRIME`  
**Owner:** `MrhRafi3`  
**Visibility:** `PUBLIC` (`isPrivate: false`)  
**Default Branch:** `main`  
**Authenticated GitHub Account:** `MrhRafi3`  
**Publish Date:** 2026-11-26  

---

## 1. Pre-Publishing Security & Privacy Audit

- **Tracked File Scan (`git ls-files`):** Confirmed **zero** `.venv/`, `__pycache__/`, `*.pyc`, `*.db`, `*.sqlite`, `*.log`, `*.safetensors` model weights, `.env`, SSH private keys, or `.DS_Store` files are tracked.
- **Model Weights Exclusion:** Local MLX model weights remain strictly outside the repository at `~/Library/Application Support/PRIME/models/` (`qwen2.5-1.5b-4bit`, `qwen3-1.7b-4bit`) and were never committed or pushed.
- **Credential & Secret Scan:** Zero real API keys, bearer tokens, passwords, or authentication secrets exist in tracked files or commit history. Synthetic dummy strings in `tests/unit/test_logging.py` exist solely to test `SecretRedactionFilter`.
- **Historical Local Path Disclosure Note:** Pre-publishing scanning detected one benign local workspace path (`/Users/.../PRIME/`) in `phase-03-reports/UI_SETUP_GUIDE.md` introduced in Phase 03 commit `3587c8c`. Per user policy (no Git history rewriting or force-pushing), existing Phase 02–04 commits were preserved intact and a separate forward documentation cleanup commit (`9a2ffa8981b5b776111740ab31a1a975754cc663`) replaced that path in `HEAD` with a portable relative reference.

---

## 2. License & Attribution Verification

- **PRIME Original Code:** Licensed under the [MIT License](LICENSE) (`Copyright (c) 2026 MrhRafi3`).
- **Original `VISION-1.2` Attribution:** Preserved verbatim (`Copyright (c) 2026 Vision Assistant contributors`, MIT) in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **Third-Party Runtime Notices:** `PySide6-Essentials` (`6.10.3`) & `shiboken6` (`6.10.3`) documented under **LGPLv3**; `mlx` (`0.32.5`), `mlx-lm` (`0.32.2`), `mlx-metal` (`0.32.5`) documented under **MIT**; `huggingface-hub`, `transformers`, `tokenizers`, `safetensors`, `sentencepiece` documented under **Apache-2.0**.

---

## 3. Published Commit History & Remote Configuration

- **Remote (`origin`):** `https://github.com/MrhRafi3/PRIME.git`
- **Preserved Phase Commits Pushed on `main`:**
  1. `b4505c58b4db3f7dc95feeeda140e778d38a0448` — `chore(phase-02): initialize PRIME independent foundation and core infrastructure`
  2. `3587c8cc8032a84814e983a57953b0f9007b9f77` — `feat(phase-03): implement PySide6 QML JARVIS desktop UI and telemetry bridge`
  3. `0dcc4b973f0dd64ea7a434b37e4346531cda813f` — `feat(phase-04): implement offline MLX-LM intelligence engine, benchmarks, and UI streaming`
  4. `9a2ffa8981b5b776111740ab31a1a975754cc663` — `docs(phase-03): replace local absolute workspace path with relative path in UI setup guide`
  5. *(Followed by this report commit)*

---

## 4. Repository Size & Post-Push Verification

- **Local Object Store / Transfer Size:** `180` objects pushed (`1.15 MiB` compressed transfer; ~`1.76 MiB` loose pre-push object store).
- **Verification Results:**
  - `gh repo view MrhRafi3/PRIME` confirmed `PUBLIC` visibility, owner `MrhRafi3`, and default branch `main`.
  - `git ls-remote origin refs/heads/main` matched local `HEAD` exactly before and after pushing.
  - No force-push or history rewrite occurred.

---

## 5. Remaining Limitations

- Phase 05 (offline voice/audio capture, STT/TTS, double-clap audio trigger) and future Windows adapters are not yet implemented.
- Historical commit `3587c8c` retains the non-sensitive directory path string in Git history because history rewriting was intentionally avoided.
