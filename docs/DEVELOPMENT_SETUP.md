# Development Setup

## Prerequisites

- **Hardware:** Apple Silicon Mac (primary target: MacBook Air M1, 8 GB unified memory)
- **OS:** macOS
- **Tools:** `uv` (`>=0.13`) and `git`

## Environment Bootstrap

PRIME uses an isolated **Python 3.12 (`arm64`)** virtual environment managed by `uv`:

```bash
cd PRIME
uv python install 3.12
uv sync --group dev
```

Verify the environment without installing any AI runtimes or modifying system Python:

```bash
uv run python scripts/check_env.py
uv run prime --version
```

## Running Tests & Static Checks

```bash
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
```

## Local Configuration Overrides

Copy `.env.example` or create `~/Library/Application Support/PRIME/config.toml`.
Never commit `.env`, `.db`, or `.log` files.
