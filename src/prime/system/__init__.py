"""Platform Abstraction Layer (PAL) for PRIME."""

from prime.system.base import (
    BatteryStatus,
    FolderOperationResult,
    PlatformCommandError,
    PlatformKind,
    SystemController,
    SystemInfo,
    SystemMetrics,
    UnsupportedPlatformError,
    VolumeStatus,
)
from prime.system.factory import create_system_controller, detect_platform

__all__ = [
    "BatteryStatus",
    "FolderOperationResult",
    "PlatformCommandError",
    "PlatformKind",
    "SystemController",
    "SystemInfo",
    "SystemMetrics",
    "UnsupportedPlatformError",
    "VolumeStatus",
    "create_system_controller",
    "detect_platform",
]
