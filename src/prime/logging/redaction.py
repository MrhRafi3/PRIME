"""Secret and private-content redaction utilities for PRIME logs."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

REDACTED = "[REDACTED]"
PRIVATE_REDACTED = "[PRIVATE_CONTENT_REDACTED]"

PRIVATE_FIELD_KEYS = frozenset(
    {
        "transcript",
        "prompt",
        "response",
        "message_text",
        "conversation",
        "note_content",
        "audio_bytes",
        "raw_audio",
    }
)

_SECRET_KEY_WORDS = frozenset(
    {"api_key", "apikey", "token", "secret", "password", "passwd", "authorization", "credential"}
)

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    # OpenAI / Anthropic / generic sk-* tokens
    re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}\b"),
    # GitHub tokens
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{16,}\b"),
    # Google API keys
    re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"),
    # Bearer tokens
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{10,}"),
    # Key=value or key: value secrets
    re.compile(
        r"(?i)\b(api_key|apikey|token|secret|password|passwd|auth_token)\b(\s*[:=]\s*)(['\"]?)([^\s,'\";]+)\3"
    ),
)


def redact_text(text: str) -> str:
    """Scrub secret tokens and key/value credentials from log strings."""
    result = text
    for idx, pattern in enumerate(_SECRET_PATTERNS):
        if idx == 4:
            result = pattern.sub(rf"\1\2{REDACTED}", result)
        else:
            result = pattern.sub(REDACTED, result)
    return result


def redact_mapping(data: Mapping[str, Any], *, log_private_content: bool = False) -> dict[str, Any]:
    """Recursively redact sensitive keys and private conversation payloads."""
    sanitized: dict[str, Any] = {}
    for raw_key, value in data.items():
        key = str(raw_key)
        lower_key = key.lower()
        if any(secret_word in lower_key for secret_word in _SECRET_KEY_WORDS):
            sanitized[key] = REDACTED
        elif not log_private_content and lower_key in PRIVATE_FIELD_KEYS:
            sanitized[key] = PRIVATE_REDACTED
        elif isinstance(value, Mapping):
            sanitized[key] = redact_mapping(value, log_private_content=log_private_content)
        elif isinstance(value, (list, tuple)):
            sanitized[key] = [
                redact_mapping(item, log_private_content=log_private_content)
                if isinstance(item, Mapping)
                else (redact_text(item) if isinstance(item, str) else item)
                for item in value
            ]
        elif isinstance(value, str):
            sanitized[key] = redact_text(value)
        else:
            sanitized[key] = value
    return sanitized


class SecretRedactionFilter(logging.Filter):
    """Logging filter that enforces secret and private-content redaction on every record."""

    def __init__(self, *, log_private_content: bool = False) -> None:
        super().__init__()
        self.log_private_content = log_private_content

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    redact_text(arg) if isinstance(arg, str) else arg for arg in record.args
                )
            elif isinstance(record.args, Mapping):
                record.args = redact_mapping(
                    record.args, log_private_content=self.log_private_content
                )
        extra_context = getattr(record, "prime_context", None)
        if isinstance(extra_context, Mapping):
            record.prime_context = redact_mapping(
                extra_context, log_private_content=self.log_private_content
            )
        return True
