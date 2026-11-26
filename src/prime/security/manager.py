"""Central security gatekeeper enforcing risk tiers, permissions, and input safety."""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from prime.config.settings import SecurityConfig
from prime.logging.logger import get_logger, log_event
from prime.security.policy import (
    ActionDeniedError,
    ConfirmationRequiredError,
    PermissionDeniedError,
    UnsafeInputError,
)
from prime.security.tiers import (
    ActionRequest,
    ConfirmationHandler,
    PermissionChecker,
    PermissionState,
    RiskTier,
)

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


class SecurityManager:
    """Enforces Tier 0/1/2 authorization, input sanitization, and allowlists."""

    def __init__(
        self,
        config: SecurityConfig,
        *,
        permission_checker: PermissionChecker | None = None,
        confirmation_handler: ConfirmationHandler | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._config = config
        self._permission_checker = permission_checker
        self._confirmation_handler = confirmation_handler
        self._logger = logger or get_logger("prime.security")

    def set_permission_checker(self, checker: PermissionChecker) -> None:
        self._permission_checker = checker

    def set_confirmation_handler(self, handler: ConfirmationHandler | None) -> None:
        self._confirmation_handler = handler

    def authorize(self, request: ActionRequest) -> None:
        """Authorize an ActionRequest or raise a SecurityError."""
        if self._permission_checker is not None:
            state = self._permission_checker.check_permission(request.scope)
            if state != PermissionState.GRANTED:
                log_event(
                    self._logger,
                    logging.WARNING,
                    "security.permission_missing",
                    (
                        f"Action '{request.action_name}' blocked; "
                        f"permission '{request.scope.value}' is {state.value}"
                    ),
                    context={
                        "action": request.action_name,
                        "scope": request.scope.value,
                        "state": state.value,
                    },
                )
                raise PermissionDeniedError(
                    f"Missing permission '{request.scope.value}' ({state.value}) "
                    f"for '{request.action_name}'."
                )

        if request.tier == RiskTier.TIER_0_READ_ONLY:
            log_event(
                self._logger,
                logging.DEBUG,
                "security.authorized",
                f"Tier 0 action authorized: {request.action_name}",
                context={"action": request.action_name, "tier": int(request.tier)},
            )
            return

        if request.tier == RiskTier.TIER_1_REVERSIBLE:
            log_event(
                self._logger,
                logging.INFO,
                "security.authorized",
                f"Tier 1 action authorized: {request.action_name}",
                context={"action": request.action_name, "tier": int(request.tier)},
            )
            return

        if request.tier == RiskTier.TIER_2_SENSITIVE_CONFIRM:
            if self._confirmation_handler is None:
                log_event(
                    self._logger,
                    logging.WARNING,
                    "security.confirmation_unavailable",
                    f"Tier 2 action '{request.action_name}' denied without confirmation handler.",
                    context={"action": request.action_name},
                )
                raise ConfirmationRequiredError(
                    f"Action '{request.action_name}' requires explicit user confirmation."
                )
            approved = bool(self._confirmation_handler.request_confirmation(request))
            if not approved:
                log_event(
                    self._logger,
                    logging.INFO,
                    "security.confirmation_denied",
                    f"User denied Tier 2 action '{request.action_name}'.",
                    context={"action": request.action_name},
                )
                raise ActionDeniedError(f"User denied Tier 2 action '{request.action_name}'.")
            log_event(
                self._logger,
                logging.INFO,
                "security.tier2_confirmed",
                f"User confirmed Tier 2 action '{request.action_name}'.",
                context={"action": request.action_name},
            )
            return

        raise ActionDeniedError(f"Unknown risk tier: {request.tier!r}")

    def validate_sandbox_path(self, relative_name: str, *, root: Path | None = None) -> Path:
        """Validate a relative path/folder name strictly inside sandbox_root."""
        if not isinstance(relative_name, str):
            raise UnsafeInputError("Path input must be a string.")
        cleaned = relative_name.strip()
        if not cleaned or _CONTROL_CHARS_RE.search(cleaned):
            raise UnsafeInputError("Path contains empty or control characters.")
        if cleaned.startswith(("/", "\\", "~")):
            raise UnsafeInputError("Absolute or home-relative paths are not allowed.")

        candidate = Path(cleaned)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise UnsafeInputError("Path traversal ('..') or absolute paths are prohibited.")

        base = (root or self._config.sandbox_root).resolve()
        resolved = (base / candidate).resolve()
        if resolved == base or not resolved.is_relative_to(base):
            raise UnsafeInputError("Resolved path escapes the allowed sandbox root.")
        return resolved

    def validate_app_name(self, app_name: str) -> str:
        """Verify an application name is strictly in the configured allowlist."""
        if (
            not isinstance(app_name, str)
            or not app_name.strip()
            or _CONTROL_CHARS_RE.search(app_name)
        ):
            raise UnsafeInputError("Invalid application name.")
        normalized = app_name.strip()
        lookup = {allowed.lower(): allowed for allowed in self._config.allowed_apps}
        matched = lookup.get(normalized.lower())
        if matched is None:
            raise ActionDeniedError(f"Application '{normalized}' is not in the PRIME allowlist.")
        return matched

    def validate_url(self, url: str) -> str:
        """Verify URL uses an allowlisted scheme and has a valid host."""
        if not isinstance(url, str) or not url.strip() or _CONTROL_CHARS_RE.search(url):
            raise UnsafeInputError("Invalid URL input.")
        trimmed = url.strip()
        parsed = urlparse(trimmed)
        if parsed.scheme.lower() not in self._config.allowed_url_schemes:
            raise UnsafeInputError(f"Disallowed URL scheme: {parsed.scheme!r}")
        if not parsed.netloc:
            raise UnsafeInputError("URL must include a valid network host.")
        return trimmed

    @staticmethod
    def verify_sha256(file_path: Path, expected_sha256: str) -> bool:
        """Verify file integrity against an expected SHA-256 hex digest."""
        digest = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return hmac.compare_digest(digest.hexdigest().lower(), expected_sha256.strip().lower())
