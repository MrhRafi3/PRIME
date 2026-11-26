"""Security tests for permissions, confirmation tiers, and unsafe input rejection."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from prime.config import SecurityConfig
from prime.plugins import PluginCapability, PluginManifest, PluginPolicyError, PluginRegistry
from prime.security import (
    ActionDeniedError,
    ActionRequest,
    ConfirmationRequiredError,
    PermissionDeniedError,
    PermissionScope,
    PermissionState,
    RiskTier,
    SecurityManager,
    UnsafeInputError,
)


class _StaticPermissionChecker:
    def __init__(self, state: PermissionState) -> None:
        self._state = state

    def check_permission(self, scope: PermissionScope) -> PermissionState:
        return self._state


class _FixedConfirmation:
    def __init__(self, decision: bool) -> None:
        self._decision = decision

    def request_confirmation(self, request: ActionRequest) -> bool:
        return self._decision


@pytest.mark.security
def test_tier_authorization_and_permission_enforcement(tmp_path: Path) -> None:
    cfg = SecurityConfig(sandbox_root=tmp_path)
    sec = SecurityManager(cfg, permission_checker=_StaticPermissionChecker(PermissionState.GRANTED))

    sec.authorize(
        ActionRequest("read_batt", RiskTier.TIER_0_READ_ONLY, PermissionScope.SYSTEM_READ)
    )
    sec.authorize(
        ActionRequest("set_vol", RiskTier.TIER_1_REVERSIBLE, PermissionScope.AUDIO_VOLUME)
    )

    # Tier 2 without confirmation handler fails closed
    t2_req = ActionRequest("open_url", RiskTier.TIER_2_SENSITIVE_CONFIRM, PermissionScope.URL_OPEN)
    with pytest.raises(ConfirmationRequiredError):
        sec.authorize(t2_req)

    # Tier 2 denied by user raises ActionDeniedError
    sec.set_confirmation_handler(_FixedConfirmation(False))
    with pytest.raises(ActionDeniedError):
        sec.authorize(t2_req)

    # Tier 2 approved by user succeeds
    sec.set_confirmation_handler(_FixedConfirmation(True))
    sec.authorize(t2_req)

    # Missing OS permission always fails safely even for Tier 0
    sec.set_permission_checker(_StaticPermissionChecker(PermissionState.NOT_DETERMINED))
    with pytest.raises(PermissionDeniedError):
        sec.authorize(
            ActionRequest("mic_read", RiskTier.TIER_0_READ_ONLY, PermissionScope.MICROPHONE)
        )


@pytest.mark.security
@pytest.mark.parametrize(
    "bad_path",
    [
        "",
        "   ",
        "../outside",
        "sub/../../outside",
        "/etc/passwd",
        "~/Desktop",
        "bad\x00name",
        ".",
    ],
)
def test_sandbox_path_traversal_blocked(tmp_path: Path, bad_path: str) -> None:
    sec = SecurityManager(SecurityConfig(sandbox_root=tmp_path))
    with pytest.raises(UnsafeInputError):
        sec.validate_sandbox_path(bad_path)


@pytest.mark.security
def test_symlink_escape_blocked(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    outside = tmp_path / "outside"
    sandbox.mkdir()
    outside.mkdir()
    escape_link = sandbox / "escape"
    escape_link.symlink_to(outside)

    sec = SecurityManager(SecurityConfig(sandbox_root=sandbox))
    with pytest.raises(UnsafeInputError):
        sec.validate_sandbox_path("escape/secret_dir")


@pytest.mark.security
def test_app_allowlist_url_validation_and_sha256(tmp_path: Path) -> None:
    sec = SecurityManager(SecurityConfig(sandbox_root=tmp_path))

    assert sec.validate_app_name("safari") == "Safari"
    with pytest.raises(ActionDeniedError):
        sec.validate_app_name("Bash")

    assert sec.validate_url("https://example.com") == "https://example.com"
    for bad_url in ("file:///etc/passwd", "javascript:alert(1)", "http://", "ftp://example.com"):
        with pytest.raises(UnsafeInputError):
            sec.validate_url(bad_url)

    sample = tmp_path / "artifact.bin"
    sample.write_bytes(b"prime-verified-payload")
    good_hex = hashlib.sha256(b"prime-verified-payload").hexdigest()
    assert sec.verify_sha256(sample, good_hex) is True
    assert sec.verify_sha256(sample, "0" * 64) is False


@pytest.mark.security
def test_plugin_network_capability_blocked_by_default(tmp_path: Path) -> None:
    class _DummyPlugin:
        def __init__(self, manifest: PluginManifest) -> None:
            self.manifest = manifest

        def initialize(self) -> None:
            pass

        def shutdown(self) -> None:
            pass

    registry = PluginRegistry(SecurityConfig(sandbox_root=tmp_path, allow_network_plugins=False))
    net_plugin = _DummyPlugin(
        PluginManifest(
            plugin_id="net_test",
            name="Net Test",
            version="0.1.0",
            capabilities=(PluginCapability.NETWORK,),
        )
    )
    with pytest.raises(PluginPolicyError):
        registry.register(net_plugin)

    local_plugin = _DummyPlugin(
        PluginManifest(
            plugin_id="local_notes",
            name="Local Notes",
            version="0.1.0",
            capabilities=(PluginCapability.READ_MEMORY,),
        )
    )
    registry.register(local_plugin)
    assert len(registry.list_manifests()) == 1
    registry.unregister_all()
