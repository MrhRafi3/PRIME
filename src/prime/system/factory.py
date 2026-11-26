"""Platform controller factory separating OS adapters from core logic."""

from __future__ import annotations

import logging
import sys

from prime.config.settings import PrimeConfig
from prime.security.manager import SecurityManager
from prime.system.base import PlatformKind, SystemController, UnsupportedPlatformError
from prime.system.macos.controller import MacOSSystemController


def detect_platform(platform_name: str | None = None) -> PlatformKind:
    """Map Python sys.platform strings to PRIME PlatformKind."""
    plat = (platform_name or sys.platform).lower()
    if plat == "darwin":
        return PlatformKind.MACOS
    if plat.startswith("win"):
        return PlatformKind.WINDOWS
    if plat.startswith("linux"):
        return PlatformKind.LINUX
    return PlatformKind.UNKNOWN


def create_system_controller(
    config: PrimeConfig,
    security: SecurityManager,
    *,
    logger: logging.Logger | None = None,
    platform_name: str | None = None,
) -> SystemController:
    """Instantiate the SystemController for the current OS."""
    kind = detect_platform(platform_name)
    if kind == PlatformKind.MACOS:
        controller = MacOSSystemController(config=config, security=security, logger=logger)
        security.set_permission_checker(controller)
        return controller
    if kind == PlatformKind.WINDOWS:
        raise UnsupportedPlatformError(
            "Windows SystemController adapter is not implemented in Phase 02."
        )
    raise UnsupportedPlatformError(f"Unsupported operating system: {kind.value}")
