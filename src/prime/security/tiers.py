"""Security risk tiers, permission scopes, and confirmation protocols."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Protocol


class RiskTier(IntEnum):
    """Three-tier action classification per PRIME security model."""

    TIER_0_READ_ONLY = 0
    TIER_1_REVERSIBLE = 1
    TIER_2_SENSITIVE_CONFIRM = 2


class PermissionScope(StrEnum):
    """OS and capability permission scopes."""

    SYSTEM_READ = "system_read"
    AUDIO_VOLUME = "audio_volume"
    APP_LAUNCH = "app_launch"
    FILESYSTEM_SANDBOX = "filesystem_sandbox"
    URL_OPEN = "url_open"
    MICROPHONE = "microphone"
    CAMERA = "camera"
    SCREEN_RECORDING = "screen_recording"
    AUTOMATION = "automation"


class PermissionState(StrEnum):
    GRANTED = "granted"
    DENIED = "denied"
    NOT_DETERMINED = "not_determined"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ActionRequest:
    """Describes an operation submitted for security authorization."""

    action_name: str
    tier: RiskTier
    scope: PermissionScope
    target: str = ""
    reason: str = ""


class ConfirmationHandler(Protocol):
    """Callback protocol for explicit Tier 2 user confirmation."""

    def request_confirmation(self, request: ActionRequest) -> bool:
        """Return True only if the user explicitly approves this action."""


class PermissionChecker(Protocol):
    """Protocol implemented by platform controllers to report permission readiness."""

    def check_permission(self, scope: PermissionScope) -> PermissionState:
        """Check whether the given permission scope is currently granted."""
