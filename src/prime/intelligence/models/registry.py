"""Approved M1 8GB model shortlist and offline local path validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from prime.config.settings import MemoryProfile


class ModelSecurityError(ValueError):
    """Raised when a model path or slug violates PRIME local model security policy."""


@dataclass(frozen=True, slots=True)
class ApprovedModelSpec:
    slug: str
    display_name: str
    repo_id: str
    download_size_gb: float
    estimated_ram_mb: int
    memory_profile: MemoryProfile
    license_name: str
    max_context_tokens: int
    supports_bangla: bool = True
    recommended: bool = False


APPROVED_MODELS: dict[str, ApprovedModelSpec] = {
    "qwen2.5-1.5b-4bit": ApprovedModelSpec(
        slug="qwen2.5-1.5b-4bit",
        display_name="Qwen 2.5 1.5B Instruct (4-bit MLX)",
        repo_id="mlx-community/Qwen2.5-1.5B-Instruct-4bit",
        download_size_gb=0.90,
        estimated_ram_mb=1400,
        memory_profile=MemoryProfile.ECO,
        license_name="Apache-2.0",
        max_context_tokens=4096,
        supports_bangla=True,
    ),
    "qwen3-1.7b-4bit": ApprovedModelSpec(
        slug="qwen3-1.7b-4bit",
        display_name="Qwen 3 1.7B (4-bit MLX)",
        repo_id="mlx-community/Qwen3-1.7B-4bit",
        download_size_gb=1.15,
        estimated_ram_mb=1650,
        memory_profile=MemoryProfile.ECO,
        license_name="Apache-2.0",
        max_context_tokens=4096,
        supports_bangla=True,
    ),
    "qwen2.5-3b-4bit": ApprovedModelSpec(
        slug="qwen2.5-3b-4bit",
        display_name="Qwen 2.5 3B Instruct (4-bit MLX)",
        repo_id="mlx-community/Qwen2.5-3B-Instruct-4bit",
        download_size_gb=1.75,
        estimated_ram_mb=2450,
        memory_profile=MemoryProfile.BALANCED,
        license_name="Apache-2.0",
        max_context_tokens=4096,
        supports_bangla=True,
        recommended=True,
    ),
    "llama-3.2-3b-4bit": ApprovedModelSpec(
        slug="llama-3.2-3b-4bit",
        display_name="Llama 3.2 3B Instruct (4-bit MLX)",
        repo_id="mlx-community/Llama-3.2-3B-Instruct-4bit",
        download_size_gb=1.85,
        estimated_ram_mb=2550,
        memory_profile=MemoryProfile.BALANCED,
        license_name="Llama-3.2-Community",
        max_context_tokens=4096,
        supports_bangla=True,
    ),
}


class ModelRegistry:
    """Manages approved local model directories without automatic downloads."""

    def __init__(
        self,
        models_dir: Path,
        *,
        catalog: dict[str, ApprovedModelSpec] | None = None,
    ) -> None:
        self._models_dir = models_dir
        self._catalog = dict(catalog if catalog is not None else APPROVED_MODELS)

    @property
    def models_dir(self) -> Path:
        return self._models_dir

    def list_catalog(self) -> tuple[ApprovedModelSpec, ...]:
        return tuple(self._catalog.values())

    def get_spec(self, slug: str) -> ApprovedModelSpec:
        clean = slug.strip()
        if clean not in self._catalog:
            raise ModelSecurityError(f"Unapproved or unknown model slug: {slug!r}")
        return self._catalog[clean]

    def resolve_model_path(self, slug: str) -> Path:
        """Resolve an approved model directory strictly inside models_dir."""
        spec = self.get_spec(slug)
        if "/" in spec.slug or "\\" in spec.slug or ".." in spec.slug:
            raise ModelSecurityError(f"Invalid model slug path: {spec.slug!r}")
        base = self._models_dir.resolve()
        candidate = (base / spec.slug).resolve()
        if candidate == base or not candidate.is_relative_to(base):
            raise ModelSecurityError("Resolved model path escapes approved models directory.")
        return candidate

    def is_installed(self, slug: str) -> bool:
        """Check whether valid local model files (config + safetensors) exist offline."""
        try:
            model_path = self.resolve_model_path(slug)
        except ModelSecurityError:
            return False
        if not model_path.is_dir():
            return False
        has_config = (model_path / "config.json").is_file()
        has_weights = any(model_path.glob("*.safetensors"))
        return has_config and has_weights

    def list_installed(self) -> tuple[ApprovedModelSpec, ...]:
        return tuple(spec for spec in self._catalog.values() if self.is_installed(spec.slug))

    def installed_size_mb(self, slug: str) -> float:
        if not self.is_installed(slug):
            return 0.0
        model_path = self.resolve_model_path(slug)
        total_bytes = sum(f.stat().st_size for f in model_path.rglob("*") if f.is_file())
        return round(total_bytes / (1024 * 1024), 1)
