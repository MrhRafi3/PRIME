"""Secure structured logging with redaction and rotating local files."""

from __future__ import annotations

from prime.logging.logger import configure_logging, get_logger, log_event
from prime.logging.redaction import (
    PRIVATE_FIELD_KEYS,
    SecretRedactionFilter,
    redact_mapping,
    redact_text,
)

__all__ = [
    "PRIVATE_FIELD_KEYS",
    "SecretRedactionFilter",
    "configure_logging",
    "get_logger",
    "log_event",
    "redact_mapping",
    "redact_text",
]
