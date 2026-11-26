"""Plugin manifest validation and capability-gated registry."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from prime.config.settings import SecurityConfig
from prime.security.tiers import RiskTier


class PluginPolicyError(PermissionError):
    """Raised when a plugin requests disallowed capabilities."""


class PluginCapability(StrEnum):
    READ_MEMORY = "read_memory"
    WRITE_MEMORY = "write_memory"
    SYSTEM_READ = "system_read"
    SYSTEM_MUTATE = "system_mutate"
    NETWORK = "network"


@dataclass(frozen=True, slots=True)
class PluginManifest:
    plugin_id: str
    name: str
    version: str
    capabilities: tuple[PluginCapability, ...]
    max_risk_tier: RiskTier = RiskTier.TIER_1_REVERSIBLE


class PluginProtocol(Protocol):
    manifest: PluginManifest

    def initialize(self) -> None:
        """Initialize plugin resources."""

    def shutdown(self) -> None:
        """Clean up plugin resources."""


class PluginRegistry:
    """Registers plugins while enforcing PRIME security and offline-first policies."""

    def __init__(self, security_config: SecurityConfig) -> None:
        self._security_config = security_config
        self._plugins: dict[str, PluginProtocol] = {}

    def register(self, plugin: PluginProtocol) -> None:
        manifest = plugin.manifest
        if not manifest.plugin_id.strip():
            raise PluginPolicyError("Plugin manifest must have a non-empty plugin_id.")
        if (
            PluginCapability.NETWORK in manifest.capabilities
            and not self._security_config.allow_network_plugins
        ):
            raise PluginPolicyError(
                f"Plugin '{manifest.plugin_id}' requires NETWORK capability, which is disabled."
            )
        if manifest.plugin_id in self._plugins:
            raise PluginPolicyError(f"Plugin '{manifest.plugin_id}' is already registered.")
        self._plugins[manifest.plugin_id] = plugin

    def list_manifests(self) -> tuple[PluginManifest, ...]:
        return tuple(p.manifest for p in self._plugins.values())

    def unregister_all(self) -> None:
        for plugin in list(self._plugins.values()):
            plugin.shutdown()
        self._plugins.clear()
