"""On-demand vision, hand-tracking, and screen OCR contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class GestureKind(StrEnum):
    NONE = "none"
    ROTATE = "rotate"
    PINCH_ZOOM = "pinch_zoom"


@dataclass(frozen=True, slots=True)
class VisionPolicy:
    """Enforces on-demand camera and Screen Recording consent."""

    camera_enabled_on_startup: bool = False
    require_explicit_camera_toggle: bool = True
    require_ocr_confirmation: bool = True


@dataclass(frozen=True, slots=True)
class GestureEvent:
    kind: GestureKind
    dx: float = 0.0
    dy: float = 0.0
    zoom_factor: float = 1.0
    hand_count: int = 0


@dataclass(frozen=True, slots=True)
class OCRResult:
    text: str
    language: str
    confidence: float = 0.0


class CameraProvider(Protocol):
    """Single-owner camera hardware abstraction."""

    @property
    def is_active(self) -> bool:
        """True only while camera hardware is explicitly open."""

    def start(self) -> None:
        """Open camera hardware after TCC permission verification."""

    def stop(self) -> None:
        """Immediately release camera hardware."""


class OCRProvider(Protocol):
    """Offline OCR abstraction (Apple Vision in future macOS phase)."""

    def recognize_image(self, image_path: Path) -> OCRResult:
        """Extract text from a local image offline."""
