"""Capability-gated plugin architecture for PRIME."""

from prime.plugins.contracts import (
    PluginCapability,
    PluginManifest,
    PluginPolicyError,
    PluginProtocol,
    PluginRegistry,
)

__all__ = [
    "PluginCapability",
    "PluginManifest",
    "PluginPolicyError",
    "PluginProtocol",
    "PluginRegistry",
]
