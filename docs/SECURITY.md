# Security & Privacy Model

## Core Commitments

- **Zero Cloud Inference or Telemetry:** `HardwareAIConfig.local_only` is enforced to `True`; network plugins are disabled by default (`allow_network_plugins=False`).
- **No Arbitrary Shell Execution:** `SecurityConfig.allow_arbitrary_shell` is locked to `False`; all `subprocess.run` calls use explicit argument lists (`shell=False`) and static macOS binary paths.
- **Three-Tier Authorization (`SecurityManager`):**
  - **Tier 0 (`TIER_0_READ_ONLY`):** Read-only diagnostics (`get_system_info`, `get_battery_status`, `get_volume`).
  - **Tier 1 (`TIER_1_REVERSIBLE`):** Reversible bounded actions (`set_volume`, `set_muted`, allowlisted `open_application`, `create_sandbox_folder`).
  - **Tier 2 (`TIER_2_SENSITIVE_CONFIRM`):** Sensitive actions (`open_url` and future screenshot/OCR/destructive operations) fail closed with `ConfirmationRequiredError` unless a `ConfirmationHandler` explicitly approves.
- **Path & URL Sanitization:**
  - `validate_sandbox_path()` rejects empty input, control characters, absolute paths, `..` segments, and symlink escapes outside `sandbox_root`.
  - `validate_url()` permits only `http`/`https` URLs with a valid network host.
- **Private Data & Log Protection:**
  - Logs (`0700` dir, `0600` file) pass through `SecretRedactionFilter`, scrubbing tokens (`sk-*`, `ghp_*`, `AIza*`, `Bearer *`, `password=...`) and redacting private fields (`transcript`, `prompt`, `response`, `raw_audio`) by default.
  - SQLite memory (`0600` file) blocks storing `MemorySensitivity.SENSITIVE` entries unless `user_approved=True` is explicitly provided.
- **Deferred Hardware TCC Prompts:** Phase 02 never invokes Microphone, Camera, Screen Recording, or Automation permission prompts.
