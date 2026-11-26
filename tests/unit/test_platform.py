"""Unit tests for Platform Abstraction Layer and macOS SystemController."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from prime.config import load_config
from prime.security import ActionRequest, PermissionScope, PermissionState, SecurityManager
from prime.system import PlatformKind, UnsupportedPlatformError, create_system_controller
from prime.system.macos import MacOSSystemController


class _AllowAllConfirmation:
    def request_confirmation(self, request: ActionRequest) -> bool:
        return True


def _make_fake_runner(responses: dict[tuple[str, ...], tuple[int, str, str]]):
    recorded: list[tuple[str, ...]] = []

    def runner(args: Sequence[str], timeout: float) -> subprocess.CompletedProcess[str]:
        key = tuple(args)
        recorded.append(key)
        code, out, err = responses.get(key, (0, "", ""))
        return subprocess.CompletedProcess(list(args), code, out, err)

    return runner, recorded


@pytest.mark.unit
def test_platform_factory_selection_and_windows_boundary(tmp_path: Path) -> None:
    cfg = load_config(
        env={"PRIME_DATA_DIR": str(tmp_path / "d"), "PRIME_LOG_DIR": str(tmp_path / "l")}
    )
    sec = SecurityManager(cfg.security)

    mac = create_system_controller(cfg, sec, platform_name="darwin")
    assert mac.platform_kind == PlatformKind.MACOS

    with pytest.raises(UnsupportedPlatformError):
        create_system_controller(cfg, sec, platform_name="win32")
    with pytest.raises(UnsupportedPlatformError):
        create_system_controller(cfg, sec, platform_name="linux")


@pytest.mark.unit
def test_macos_controller_does_not_prompt_hardware_tcc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import prime.voice.permissions as voice_perms

    def _fail_prompt(*_args, **_kwargs) -> None:
        raise AssertionError("check_permission must never invoke TCC microphone prompt")

    monkeypatch.setattr(voice_perms, "request_microphone_permission", _fail_prompt)

    cfg = load_config(
        env={"PRIME_DATA_DIR": str(tmp_path / "d"), "PRIME_LOG_DIR": str(tmp_path / "l")}
    )
    sec = SecurityManager(cfg.security)
    mac = MacOSSystemController(cfg, sec)

    assert mac.check_permission(PermissionScope.SYSTEM_READ) == PermissionState.GRANTED
    assert mac.check_permission(PermissionScope.MICROPHONE) in {
        PermissionState.NOT_DETERMINED,
        PermissionState.GRANTED,
        PermissionState.DENIED,
        PermissionState.UNAVAILABLE,
    }
    assert mac.check_permission(PermissionScope.CAMERA) == PermissionState.NOT_DETERMINED
    assert mac.check_permission(PermissionScope.SCREEN_RECORDING) == PermissionState.NOT_DETERMINED


@pytest.mark.unit
def test_macos_controller_battery_volume_and_sandbox_folder(tmp_path: Path) -> None:
    cfg_file = tmp_path / "cfg.toml"
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    cfg_file.write_text(f'[security]\nsandbox_root = "{sandbox}"\n', encoding="utf-8")
    cfg = load_config(
        config_path=cfg_file,
        env={"PRIME_DATA_DIR": str(tmp_path / "d"), "PRIME_LOG_DIR": str(tmp_path / "l")},
    )
    sec = SecurityManager(cfg.security, confirmation_handler=_AllowAllConfirmation())

    runner, recorded = _make_fake_runner(
        {
            ("/usr/bin/pmset", "-g", "batt"): (
                0,
                "Now drawing from 'Battery Power'\n"
                " -InternalBattery-0\t84%; discharging; 5:12 remaining",
                "",
            ),
            ("/usr/bin/osascript", "-e", "get volume settings"): (
                0,
                "output volume:45, input volume:50, alert volume:100, output muted:false",
                "",
            ),
        }
    )
    mac = MacOSSystemController(cfg, sec, runner=runner)
    sec.set_permission_checker(mac)

    batt = mac.get_battery_status()
    assert batt.percent == 84
    assert batt.is_charging is False

    vol = mac.get_volume()
    assert vol.percent == 45
    assert vol.is_muted is False

    updated = mac.set_volume(150)  # clamped safely to 100
    assert updated.percent == 100
    assert ("/usr/bin/osascript", "-e", "set volume output volume 100") in recorded

    folder_res = mac.create_sandbox_folder("projects")
    assert folder_res.created is True
    assert folder_res.path == (sandbox / "projects").resolve()
    assert folder_res.path.is_dir()

    app_name = mac.open_application("safari")
    assert app_name == "Safari"
    assert ("/usr/bin/open", "-a", "Safari") in recorded
