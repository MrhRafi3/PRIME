"""Safe macOS foundation SystemController using allowlisted commands only."""

from __future__ import annotations

import logging
import os
import platform
import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from prime.config.settings import PrimeConfig
from prime.logging.logger import get_logger, log_event
from prime.security.manager import SecurityManager
from prime.security.tiers import ActionRequest, PermissionScope, PermissionState, RiskTier
from prime.system.base import (
    BatteryStatus,
    FolderOperationResult,
    PlatformCommandError,
    PlatformKind,
    SystemController,
    SystemInfo,
    SystemMetrics,
    VolumeStatus,
)

CommandRunner = Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]

_PMSET_PCT_RE = re.compile(r"(\d{1,3})%")
_VOL_SETTINGS_RE = re.compile(r"output volume:(\d+).*?output muted:(true|false)")
_VM_PAGE_SIZE_RE = re.compile(r"page size of (\d+) bytes")
_VM_STAT_LINE_RE = re.compile(r"^([^:]+):\s+(\d+)\.$")


def _default_runner(args: Sequence[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        check=False,
    )


class MacOSSystemController(SystemController):
    """macOS Apple Silicon foundation adapter enforcing SecurityManager policies."""

    def __init__(
        self,
        config: PrimeConfig,
        security: SecurityManager,
        *,
        logger: logging.Logger | None = None,
        runner: CommandRunner | None = None,
    ) -> None:
        self._config = config
        self._security = security
        self._logger = logger or get_logger("prime.system.macos")
        self._runner = runner or _default_runner

    @property
    def platform_kind(self) -> PlatformKind:
        return PlatformKind.MACOS

    def check_permission(self, scope: PermissionScope) -> PermissionState:
        """Report readiness without triggering macOS TCC privacy prompts."""
        if scope in {
            PermissionScope.SYSTEM_READ,
            PermissionScope.AUDIO_VOLUME,
            PermissionScope.APP_LAUNCH,
            PermissionScope.FILESYSTEM_SANDBOX,
            PermissionScope.URL_OPEN,
        }:
            return PermissionState.GRANTED
        if scope == PermissionScope.MICROPHONE:
            from prime.voice.permissions import check_microphone_permission

            return check_microphone_permission()
        # Camera, Screen Recording, and Automation remain unprompted until built.
        return PermissionState.NOT_DETERMINED

    def _run_allowlisted(self, args: Sequence[str], *, timeout: float = 5.0) -> str:
        try:
            proc = self._runner(args, timeout)
        except Exception as exc:
            raise PlatformCommandError(f"Command execution failed: {args[0]}") from exc
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            raise PlatformCommandError(
                f"Command '{args[0]}' exited with status {proc.returncode}: {stderr}"
            )
        return (proc.stdout or "").strip()

    def get_system_info(self) -> SystemInfo:
        self._security.authorize(
            ActionRequest("get_system_info", RiskTier.TIER_0_READ_ONLY, PermissionScope.SYSTEM_READ)
        )
        os_ver = platform.mac_ver()[0] or platform.release()
        arch = platform.machine()
        cpu_brand = "Apple Silicon"
        total_mem = 0
        try:
            cpu_out = self._run_allowlisted(["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"])
            if cpu_out:
                cpu_brand = cpu_out
        except PlatformCommandError:
            pass
        try:
            mem_out = self._run_allowlisted(["/usr/sbin/sysctl", "-n", "hw.memsize"])
            total_mem = int(mem_out)
        except (PlatformCommandError, ValueError):
            total_mem = 0

        return SystemInfo(
            platform=PlatformKind.MACOS,
            os_version=os_ver,
            machine_arch=arch,
            cpu_brand=cpu_brand,
            total_memory_bytes=total_mem,
        )

    def get_battery_status(self) -> BatteryStatus:
        self._security.authorize(
            ActionRequest(
                "get_battery_status", RiskTier.TIER_0_READ_ONLY, PermissionScope.SYSTEM_READ
            )
        )
        out = self._run_allowlisted(["/usr/bin/pmset", "-g", "batt"])
        match = _PMSET_PCT_RE.search(out)
        percent = int(match.group(1)) if match else None
        lower = out.lower()
        if "ac power" in lower or ("charging" in lower and "discharging" not in lower):
            charging: bool | None = True
        elif "battery power" in lower or "discharging" in lower:
            charging = False
        else:
            charging = None
        if "ac power" in lower:
            source = "AC Power"
        elif "battery power" in lower:
            source = "Battery Power"
        else:
            source = "Unknown"
        return BatteryStatus(percent=percent, is_charging=charging, raw_source=source)

    def get_system_metrics(self) -> SystemMetrics:
        """Collect lightweight CPU, memory, and battery metrics without blocking UI."""
        self._security.authorize(
            ActionRequest(
                "get_system_metrics", RiskTier.TIER_0_READ_ONLY, PermissionScope.SYSTEM_READ
            )
        )
        cpu_pct = self._read_cpu_percent()
        mem_used_gb, mem_total_gb, mem_pct = self._read_memory_usage()
        batt_pct: int | None = None
        batt_charging: bool | None = None
        try:
            batt = self.get_battery_status()
            batt_pct = batt.percent
            batt_charging = batt.is_charging
        except PlatformCommandError:
            pass
        return SystemMetrics(
            cpu_percent=cpu_pct,
            memory_used_gb=mem_used_gb,
            memory_total_gb=mem_total_gb,
            memory_percent=mem_pct,
            battery_percent=batt_pct,
            battery_charging=batt_charging,
        )

    def _read_cpu_percent(self) -> float | None:
        try:
            out = self._run_allowlisted(["/bin/ps", "-A", "-o", "%cpu"], timeout=2.0)
        except PlatformCommandError:
            return None
        total = 0.0
        for line in out.splitlines()[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                total += float(stripped)
            except ValueError:
                continue
        cores = max(1, os.cpu_count() or 1)
        return round(max(0.0, min(100.0, total / cores)), 1)

    def _read_memory_usage(self) -> tuple[float | None, float | None, float | None]:
        try:
            total_raw = self._run_allowlisted(["/usr/sbin/sysctl", "-n", "hw.memsize"], timeout=2.0)
            total_bytes = int(total_raw)
            vm_out = self._run_allowlisted(["/usr/bin/vm_stat"], timeout=2.0)
        except (PlatformCommandError, ValueError):
            return None, None, None

        if total_bytes <= 0:
            return None, None, None

        page_match = _VM_PAGE_SIZE_RE.search(vm_out)
        page_size = int(page_match.group(1)) if page_match else 16384
        pages: dict[str, int] = {}
        for line in vm_out.splitlines():
            m = _VM_STAT_LINE_RE.match(line.strip())
            if m:
                pages[m.group(1).strip()] = int(m.group(2))

        used_pages = (
            pages.get("Pages active", 0)
            + pages.get("Pages wired down", 0)
            + pages.get("Pages occupied by compressor", 0)
        )
        if used_pages <= 0:
            return None, None, None

        used_bytes = min(total_bytes, used_pages * page_size)
        gib = 1024**3
        used_gb = round(used_bytes / gib, 2)
        total_gb = round(total_bytes / gib, 2)
        pct = round((used_bytes / total_bytes) * 100.0, 1)
        return used_gb, total_gb, pct

    def get_volume(self) -> VolumeStatus:
        self._security.authorize(
            ActionRequest("get_volume", RiskTier.TIER_0_READ_ONLY, PermissionScope.AUDIO_VOLUME)
        )
        out = self._run_allowlisted(["/usr/bin/osascript", "-e", "get volume settings"])
        match = _VOL_SETTINGS_RE.search(out.lower())
        if not match:
            return VolumeStatus(percent=None, is_muted=None)
        return VolumeStatus(percent=int(match.group(1)), is_muted=(match.group(2) == "true"))

    def set_volume(self, level: int) -> VolumeStatus:
        if isinstance(level, bool) or not isinstance(level, int):
            raise ValueError("Volume level must be an integer.")
        clamped = max(0, min(100, level))
        self._security.authorize(
            ActionRequest(
                "set_volume",
                RiskTier.TIER_1_REVERSIBLE,
                PermissionScope.AUDIO_VOLUME,
                target=str(clamped),
            )
        )
        # Integer is strictly clamped and serialized safely without user string interpolation.
        self._run_allowlisted(["/usr/bin/osascript", "-e", f"set volume output volume {clamped}"])
        if clamped > 0:
            self._run_allowlisted(["/usr/bin/osascript", "-e", "set volume without output muted"])
        log_event(
            self._logger,
            logging.INFO,
            "macos.volume_changed",
            "System output volume updated",
            context={"level": clamped},
        )
        return VolumeStatus(percent=clamped, is_muted=(clamped == 0))

    def set_muted(self, muted: bool) -> VolumeStatus:
        self._security.authorize(
            ActionRequest(
                "set_muted",
                RiskTier.TIER_1_REVERSIBLE,
                PermissionScope.AUDIO_VOLUME,
                target="mute" if muted else "unmute",
            )
        )
        script = "set volume with output muted" if muted else "set volume without output muted"
        self._run_allowlisted(["/usr/bin/osascript", "-e", script])
        return VolumeStatus(percent=None, is_muted=bool(muted))

    def open_application(self, app_name: str) -> str:
        validated_app = self._security.validate_app_name(app_name)
        self._security.authorize(
            ActionRequest(
                "open_application",
                RiskTier.TIER_1_REVERSIBLE,
                PermissionScope.APP_LAUNCH,
                target=validated_app,
            )
        )
        self._run_allowlisted(["/usr/bin/open", "-a", validated_app])
        return validated_app

    def open_url(self, url: str) -> str:
        validated_url = self._security.validate_url(url)
        self._security.authorize(
            ActionRequest(
                "open_url",
                RiskTier.TIER_2_SENSITIVE_CONFIRM,
                PermissionScope.URL_OPEN,
                target=validated_url,
                reason="Open external URL in default browser",
            )
        )
        self._run_allowlisted(["/usr/bin/open", validated_url])
        return validated_url

    def create_sandbox_folder(self, folder_name: str) -> FolderOperationResult:
        target_path: Path = self._security.validate_sandbox_path(folder_name)
        self._security.authorize(
            ActionRequest(
                "create_sandbox_folder",
                RiskTier.TIER_1_REVERSIBLE,
                PermissionScope.FILESYSTEM_SANDBOX,
                target=str(target_path),
            )
        )
        if target_path.exists():
            return FolderOperationResult(path=target_path, created=False)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.mkdir(exist_ok=False)
        return FolderOperationResult(path=target_path, created=True)
