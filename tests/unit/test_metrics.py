"""Unit tests for SystemMetrics collection and TOML config persistence."""

from __future__ import annotations

import stat
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from prime.config import LanguageMode, MemoryProfile, load_config, save_config_toml
from prime.security import SecurityManager
from prime.system.macos import MacOSSystemController


def _fake_runner(responses: dict[tuple[str, ...], tuple[int, str, str]]):
    def runner(args: Sequence[str], timeout: float) -> subprocess.CompletedProcess[str]:
        code, out, err = responses.get(tuple(args), (1, "", "unavailable"))
        return subprocess.CompletedProcess(list(args), code, out, err)

    return runner


@pytest.mark.unit
def test_macos_system_metrics_parsing_and_graceful_unavailable(tmp_path: Path) -> None:
    cfg = load_config(
        env={"PRIME_DATA_DIR": str(tmp_path / "d"), "PRIME_LOG_DIR": str(tmp_path / "l")}
    )
    sec = SecurityManager(cfg.security)

    vm_sample = (
        "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
        "Pages active:                            120000.\n"
        "Pages wired down:                         80000.\n"
        "Pages occupied by compressor:             40000.\n"
    )
    runner = _fake_runner(
        {
            ("/bin/ps", "-A", "-o", "%cpu"): (0, "%CPU\n 40.0\n 40.0\n", ""),
            ("/usr/sbin/sysctl", "-n", "hw.memsize"): (0, "8589934592\n", ""),
            ("/usr/bin/vm_stat",): (0, vm_sample, ""),
            ("/usr/bin/pmset", "-g", "batt"): (
                0,
                "Now drawing from 'AC Power'\n -InternalBattery-0\t91%; charging; 0:20 remaining",
                "",
            ),
        }
    )
    mac = MacOSSystemController(cfg, sec, runner=runner)
    sec.set_permission_checker(mac)

    metrics = mac.get_system_metrics()
    assert metrics.cpu_percent is not None
    assert 0.0 <= metrics.cpu_percent <= 100.0
    assert metrics.memory_total_gb == 8.0
    assert metrics.memory_used_gb is not None
    assert metrics.memory_percent is not None
    assert metrics.battery_percent == 91
    assert metrics.battery_charging is True

    # All commands failing should gracefully yield None fields instead of raising
    broken_mac = MacOSSystemController(cfg, sec, runner=_fake_runner({}))
    sec.set_permission_checker(broken_mac)
    empty = broken_mac.get_system_metrics()
    assert empty.cpu_percent is None
    assert empty.memory_used_gb is None
    assert empty.memory_total_gb is None
    assert empty.memory_percent is None
    assert empty.battery_percent is None
    assert empty.battery_charging is None


@pytest.mark.unit
def test_save_config_toml_roundtrip_and_permissions(tmp_path: Path) -> None:
    cfg_path = tmp_path / "cfg" / "config.toml"
    cfg = load_config(
        env={"PRIME_DATA_DIR": str(tmp_path / "d"), "PRIME_LOG_DIR": str(tmp_path / "l")}
    )
    saved = save_config_toml(cfg, path=cfg_path)
    assert saved == cfg_path
    assert stat.S_IMODE(cfg_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(cfg_path.stat().st_mode) == 0o600

    reloaded = load_config(config_path=cfg_path, env={})
    assert reloaded.identity.bundle_id == "com.mrhrafi3.prime"
    assert reloaded.ai.memory_profile == MemoryProfile.BALANCED
    assert reloaded.ai.language_mode == LanguageMode.BANGLA_ENGLISH
    assert reloaded.activation.double_clap_enabled is True
    assert reloaded.activation.wake_word_enabled is False
