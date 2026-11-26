"""Approved local STT model catalog with SHA-256 verification."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from pathlib import Path


class STTModelSecurityError(ValueError):
    """Raised when an STT model slug or path violates security policy."""


@dataclass(frozen=True, slots=True)
class ApprovedSTTModel:
    slug: str
    display_name: str
    filename: str
    repo_id: str
    size_mb: float
    estimated_ram_mb: int
    sha256: str
    license_name: str = "MIT"
    supports_bangla: bool = True


APPROVED_STT_MODELS: dict[str, ApprovedSTTModel] = {
    "whisper-small-q5_1": ApprovedSTTModel(
        slug="whisper-small-q5_1",
        display_name="Whisper Small (q5_1)",
        filename="ggml-small-q5_1.bin",
        repo_id="ggerganov/whisper.cpp",
        size_mb=181.3,
        estimated_ram_mb=500,
        sha256="ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb",
        license_name="MIT",
        supports_bangla=True,
    ),
    "whisper-large-v3-turbo-q5_0": ApprovedSTTModel(
        slug="whisper-large-v3-turbo-q5_0",
        display_name="Whisper Large-v3-Turbo (q5_0)",
        filename="ggml-large-v3-turbo-q5_0.bin",
        repo_id="ggerganov/whisper.cpp",
        size_mb=547.4,
        estimated_ram_mb=1100,
        sha256="394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2",
        license_name="MIT",
        supports_bangla=True,
    ),
}


class STTModelRegistry:
    """Manages local GGML Whisper weights strictly inside stt_dir."""

    def __init__(
        self,
        stt_dir: Path,
        *,
        catalog: dict[str, ApprovedSTTModel] | None = None,
    ) -> None:
        self._stt_dir = stt_dir
        self._catalog = dict(catalog if catalog is not None else APPROVED_STT_MODELS)

    @property
    def stt_dir(self) -> Path:
        return self._stt_dir

    def list_catalog(self) -> tuple[ApprovedSTTModel, ...]:
        return tuple(self._catalog.values())

    def get_spec(self, slug: str) -> ApprovedSTTModel:
        clean = slug.strip()
        if clean not in self._catalog:
            raise STTModelSecurityError(f"Unknown or unapproved STT model slug: {slug!r}")
        return self._catalog[clean]

    def resolve_model_path(self, slug: str) -> Path:
        spec = self.get_spec(slug)
        if "/" in spec.filename or "\\" in spec.filename or ".." in spec.filename:
            raise STTModelSecurityError(f"Invalid STT model filename: {spec.filename!r}")
        base = self._stt_dir.resolve()
        candidate = (base / spec.filename).resolve()
        if candidate == base or not candidate.is_relative_to(base):
            raise STTModelSecurityError("Resolved STT model path escapes approved directory.")
        return candidate

    def is_installed(self, slug: str) -> bool:
        try:
            path = self.resolve_model_path(slug)
        except STTModelSecurityError:
            return False
        return path.is_file() and path.stat().st_size > 1024

    def verify_checksum(self, slug: str) -> bool:
        spec = self.get_spec(slug)
        path = self.resolve_model_path(slug)
        if not path.is_file():
            return False
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return hmac.compare_digest(digest.hexdigest().lower(), spec.sha256.lower())

    def list_installed(self) -> tuple[ApprovedSTTModel, ...]:
        return tuple(spec for spec in self._catalog.values() if self.is_installed(spec.slug))
