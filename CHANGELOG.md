# Changelog

All notable changes to PRIME will be documented in this file.

## [0.1.0] - 2026-11-26 (Phase 02 — Core Foundation)

### Added
- Independent Python 3.12 (`arm64`) project layout managed with `uv` (`pyproject.toml`, `uv.lock`).
- Centralized typed configuration (`prime.config`) with TOML/JSON support and `PRIME_*` environment overrides.
- Secure rotating local logger (`prime.logging`) with automatic token/secret redaction and private-content suppression.
- Three-tier `SecurityManager` (`prime.security`) enforcing Tier 0/1/2 rules, sandbox path traversal guards, URL validation, and app allowlists.
- Platform Abstraction Layer (`prime.system.base.SystemController`) and `MacOSSystemController` (`prime.system.macos`).
- Local SQLite + FTS5 persistent memory foundation (`prime.intelligence.memory`) with versioned migrations and parameterized CRUD.
- Multi-turn `ContextAssembler` and typed contracts for future local LLM providers, offline voice (push-to-talk / double-clap, Bangla + English), on-demand vision, and capability-gated plugins.
- Unit, integration, and security test suites (`tests/`) plus `README.md`, `docs/`, `LICENSE`, and `THIRD_PARTY_NOTICES.md`.
