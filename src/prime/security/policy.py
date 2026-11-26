"""Security exceptions and validation helpers."""

from __future__ import annotations


class SecurityError(Exception):
    """Base error for security policy violations."""


class PermissionDeniedError(SecurityError):
    """Raised when a required OS or capability permission is missing or denied."""


class ConfirmationRequiredError(SecurityError):
    """Raised when a Tier 2 action lacks explicit user confirmation."""


class ActionDeniedError(SecurityError):
    """Raised when an action is rejected by allowlist or confirmation policy."""


class UnsafeInputError(SecurityError):
    """Raised when input fails path, URL, or command sanitization."""
