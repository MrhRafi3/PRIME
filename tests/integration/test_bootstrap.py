"""Integration tests for PRIME bootstrap, event bus, and CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prime.config import load_config
from prime.core import AssistantState, PrimeApp
from prime.main import main as cli_main
from prime.system import PlatformKind


@pytest.mark.integration
def test_app_bootstrap_events_and_shutdown(tmp_path: Path) -> None:
    cfg = load_config(
        env={
            "PRIME_DATA_DIR": str(tmp_path / "data"),
            "PRIME_LOG_DIR": str(tmp_path / "logs"),
            "PRIME_ENVIRONMENT": "test",
        }
    )
    app = PrimeApp(cfg, platform_override="darwin")
    transitions: list[tuple[str, str]] = []
    app.events.subscribe(
        "assistant.state_changed",
        lambda ev: transitions.append((ev.payload["from"], ev.payload["to"])),
    )

    snap = app.bootstrap()
    assert snap.app_name == "PRIME"
    assert snap.bundle_id == "com.mrhrafi3.prime"
    assert snap.state == AssistantState.IDLE
    assert snap.platform == PlatformKind.MACOS
    assert snap.local_only is True
    assert snap.schema_version >= 2

    app.shutdown()
    assert app.state == AssistantState.STOPPED
    assert transitions == [
        ("stopped", "starting"),
        ("starting", "idle"),
        ("idle", "shutting_down"),
        ("shutting_down", "stopped"),
    ]


@pytest.mark.integration
def test_cli_config_status_and_doctor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PRIME_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PRIME_LOG_DIR", str(tmp_path / "logs"))

    assert cli_main(["config"]) == 0
    cfg_out = json.loads(capsys.readouterr().out)
    assert cfg_out["identity"]["bundle_id"] == "com.mrhrafi3.prime"

    assert cli_main(["status"]) == 0
    status_out = json.loads(capsys.readouterr().out)
    assert status_out["app_name"] == "PRIME"
    assert status_out["state"] == "idle"

    assert cli_main(["doctor"]) == 0
    doc_out = json.loads(capsys.readouterr().out)
    assert doc_out["system"]["platform"] == "macos"
    assert doc_out["system"]["arch"] == "arm64"
