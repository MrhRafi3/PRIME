# PRIME Architecture (Phase 02)

## Design Principles

1. **100% Local-First:** Zero mandatory internet connectivity, zero cloud AI APIs, zero telemetry.
2. **M1 8 GB Memory Discipline:** Standard-library core with zero always-on daemon bloat and bounded context assembly (`eco`, `balanced`, `heavy` profiles).
3. **Strict OS Isolation:** All macOS-specific commands live inside `prime.system.macos` behind the OS-neutral `SystemController` abstraction (`prime.system.base`).
4. **Fail-Closed Security:** Every system mutation passes through `SecurityManager` with risk tiers (`Tier 0/1/2`), allowlists, and path-traversal validation.

## Module Boundaries

```
src/prime/
├── main.py                     # CLI entry point (status, config, doctor)
├── core/
│   ├── events.py               # AssistantState & synchronous in-process EventBus
│   └── app.py                  # PrimeApp bootstrap, wiring, graceful shutdown
├── config/
│   └── settings.py             # Typed dataclasses, TOML/JSON + PRIME_* env overrides
├── logging/
│   ├── redaction.py            # Secret & private-content scrubbing filter
│   └── logger.py               # Rotating local JSON/text logger (0700/0600 perms)
├── security/
│   ├── tiers.py                # RiskTier (0/1/2), PermissionScope, ConfirmationHandler
│   ├── policy.py               # Security exception hierarchy
│   └── manager.py              # Authorization gatekeeper, sandbox/URL/app/SHA-256 checks
├── system/
│   ├── base.py                 # OS-neutral SystemController ABC & DTOs
│   ├── factory.py              # Platform selector (macOS implemented; Windows boundary reserved)
│   └── macos/controller.py     # Safe allowlisted macOS foundation adapter
├── intelligence/
│   ├── providers/base.py       # LLMProvider protocol & M1 8GB model profiles
│   ├── memory/
│   │   ├── schema.py           # Conversations, messages, memory_entries, FTS5 detection
│   │   ├── migrations.py       # Versioned transactional schema migrations
│   │   └── store.py            # Parameterized SQLite CRUD & sensitivity guard
│   └── context/assembler.py    # Bounded multi-turn prompt assembly (bn-en / en)
├── voice/contracts.py          # STT/TTS protocols & push-to-talk / double-clap policy
├── vision/contracts.py         # On-demand Camera/OCR/Gesture contracts
└── plugins/contracts.py        # Capability-gated plugin manifest & registry
```

## Future Platform Extension (Windows)

Adding Windows support in a future phase requires implementing `WindowsSystemController(SystemController)` under `src/prime/system/windows/` and registering it inside `prime.system.factory.create_system_controller()`. Core lifecycle, configuration, memory, security policy, and AI orchestration require zero changes.
