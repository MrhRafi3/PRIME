"""Platform-independent SystemController interface and shared models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from prime.security.tiers import PermissionChecker, PermissionScope, PermissionState


class PlatformKind(StrEnum):
    MACOS = "macos"
    WINDOWS = "windows"
    LINUX = "linux"
    UNKNOWN = "unknown"


class UnsupportedPlatformError(RuntimeError):
    """Raised when running on an OS without an active PRIME SystemController adapter."""


class PlatformCommandError(RuntimeError):
    """Raised when an allowlisted OS command fails safely."""


@dataclass(frozen=True, slots=True)
class SystemInfo:
    platform: PlatformKind
    os_version: str
    machine_arch: str
    cpu_brand: str
    total_memory_bytes: int


@dataclass(frozen=True, slots=True)
class BatteryStatus:
    percent: int | None
    is_charging: bool | None
    raw_source: str


@dataclass(frozen=True, slots=True)
class VolumeStatus:
    percent: int | None
    is_muted: bool | None


@dataclass(frozen=True, slots=True)
class SystemMetrics:
    cpu_percent: float | None
    memory_used_gb: float | None
    memory_total_gb: float | None
    memory_percent: float | None
    battery_percent: int | None
    battery_charging: bool | None


@dataclass(frozen=True, slots=True)
class FolderOperationResult:
    path: Path
    created: bool


class SystemController(PermissionChecker, ABC):
    """OS-neutral boundary isolating system operations from PRIME core and AI."""

    @property
    @abstractmethod
    def platform_kind(self) -> PlatformKind:
        """Return the concrete platform identifier."""

    @abstractmethod
    def check_permission(self, scope: PermissionScope) -> PermissionState:
        """Return current readiness for a permission scope without prompting the user."""

    @abstractmethod
    def get_system_info(self) -> SystemInfo:
        """Return basic OS and hardware metadata (Tier 0)."""

    @abstractmethod
    def get_battery_status(self) -> BatteryStatus:
        """Return power/battery state (Tier 0)."""

    @abstractmethod
    def get_system_metrics(self) -> SystemMetrics:
        """Return lightweight CPU, memory, and battery telemetry (Tier 0)."""

    @abstractmethod
    def get_volume(self) -> VolumeStatus:
        """Return output audio volume and mute state (Tier 0)."""

    @abstractmethod
    def set_volume(self, level: int) -> VolumeStatus:
        """Set output audio volume within 0..100 (Tier 1)."""

    @abstractmethod
    def set_muted(self, muted: bool) -> VolumeStatus:
        """Mute or unmute system audio output (Tier 1)."""

    @abstractmethod
    def open_application(self, app_name: str) -> str:
        """Launch an allowlisted desktop application (Tier 1)."""

    @abstractmethod
    def open_url(self, url: str) -> str:
        """Open a validated http/https URL in the default browser (Tier 2)."""

    @abstractmethod
    def create_sandbox_folder(self, folder_name: str) -> FolderOperationResult:
        """Create a folder strictly inside the configured sandbox root (Tier 1)."""
