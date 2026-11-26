"""Unit tests for PRIME structured logging, file permissions, and secret redaction."""

from __future__ import annotations

import json
import logging
import stat
from pathlib import Path

import pytest

from prime.config import LoggingConfig
from prime.logging import configure_logging, log_event, redact_text


@pytest.mark.unit
def test_redact_text_scrubs_secrets() -> None:
    raw = (
        "Using key sk-1234567890abcdef1234 and ghp_abcdefghijklmnopqrstuv "
        "with Bearer mysecrettoken12345 and password=supersecret!"
    )
    scrubbed = redact_text(raw)
    assert "sk-1234567890abcdef1234" not in scrubbed
    assert "ghp_abcdefghijklmnopqrstuv" not in scrubbed
    assert "mysecrettoken12345" not in scrubbed
    assert "supersecret!" not in scrubbed
    assert "[REDACTED]" in scrubbed


@pytest.mark.unit
def test_logging_file_permissions_and_private_content_redaction(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    cfg = LoggingConfig(level="INFO", log_private_content=False, json_format=True)
    logger = configure_logging(cfg, log_dir, logger_name="prime.test_redaction")

    log_event(
        logger,
        logging.INFO,
        "voice.sample",
        "Processed request token=secret_value_999",
        context={
            "api_key": "AIzaSyD-ExampleFakeKey1234567890",
            "transcript": "Amar nam Rafi",
            "safe_metric": 42,
        },
    )
    for h in logger.handlers:
        h.flush()

    log_file = log_dir / "prime.log"
    assert log_file.exists()
    assert stat.S_IMODE(log_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(log_file.stat().st_mode) == 0o600

    record = json.loads(log_file.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert "secret_value_999" not in record["message"]
    assert record["context"]["api_key"] == "[REDACTED]"
    assert record["context"]["transcript"] == "[PRIVATE_CONTENT_REDACTED]"
    assert record["context"]["safe_metric"] == 42
