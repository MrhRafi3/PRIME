"""Curated M1 8GB model catalog and local offline model registry."""

from prime.intelligence.models.registry import (
    APPROVED_MODELS,
    ApprovedModelSpec,
    ModelRegistry,
    ModelSecurityError,
)

__all__ = [
    "APPROVED_MODELS",
    "ApprovedModelSpec",
    "ModelRegistry",
    "ModelSecurityError",
]
