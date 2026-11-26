"""Rotating structured local logging setup for PRIME."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from prime.config.settings import LoggingConfig
from prime.logging.redaction import SecretRedactionFilter, redact_mapping, redact_text


class StructuredFormatter(logging.Formatter):
    """Formats log records as single-line JSON or readable structured text."""

    def __init__(self, *, json_format: bool = True) -> None:
        super().__init__()
        self.json_format = json_format

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        message = redact_text(record.getMessage())
        context = getattr(record, "prime_context", None)
        event = getattr(record, "prime_event", None)

        if self.json_format:
            payload: dict[str, Any] = {
                "ts": ts,
                "level": record.levelname,
                "logger": record.name,
                "message": message,
            }
            if event:
                payload["event"] = event
            if isinstance(context, Mapping) and context:
                payload["context"] = dict(context)
            if record.exc_info:
                payload["exception"] = redact_text(self.formatException(record.exc_info))
            return json.dumps(payload, ensure_ascii=False)

        ctx_suffix = f" | {dict(context)}" if isinstance(context, Mapping) and context else ""
        ev_prefix = f"[{event}] " if event else ""
        base = f"{ts} {record.levelname:<8} {record.name}: {ev_prefix}{message}{ctx_suffix}"
        if record.exc_info:
            base = f"{base}\n{redact_text(self.formatException(record.exc_info))}"
        return base


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def configure_logging(
    config: LoggingConfig,
    log_dir: Path,
    *,
    logger_name: str = "prime",
    console: bool = False,
) -> logging.Logger:
    """Configure isolated rotating local file logging for PRIME."""
    _ensure_private_dir(log_dir)
    log_file = log_dir / "prime.log"
    if not log_file.exists():
        log_file.touch(mode=0o600)
    else:
        os.chmod(log_file, 0o600)

    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, config.level))
    logger.propagate = False

    for existing in list(logger.handlers):
        existing.close()
        logger.removeHandler(existing)

    redaction_filter = SecretRedactionFilter(log_private_content=config.log_private_content)
    formatter = StructuredFormatter(json_format=config.json_format)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=config.max_bytes,
        backupCount=config.backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, config.level))
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redaction_filter)
    logger.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(getattr(logging, config.level))
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(redaction_filter)
        logger.addHandler(stream_handler)

    return logger


def get_logger(name: str = "prime") -> logging.Logger:
    """Return a child logger within the PRIME logging hierarchy."""
    if name == "prime" or name.startswith("prime."):
        return logging.getLogger(name)
    return logging.getLogger(f"prime.{name}")


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    message: str,
    *,
    context: Mapping[str, Any] | None = None,
    log_private_content: bool = False,
) -> None:
    """Emit a structured, redacted log event."""
    safe_ctx = redact_mapping(context, log_private_content=log_private_content) if context else {}
    logger.log(
        level,
        redact_text(message),
        extra={"prime_event": event, "prime_context": safe_ctx},
    )
