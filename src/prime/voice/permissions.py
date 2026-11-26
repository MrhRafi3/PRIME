"""Non-prompting macOS microphone permission checks and explicit user request helper."""

from __future__ import annotations

import threading

from prime.security.tiers import PermissionState


def check_microphone_permission() -> PermissionState:
    """Return current macOS microphone TCC state without triggering a system prompt."""
    try:
        import AVFoundation

        status = int(
            AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(
                AVFoundation.AVMediaTypeAudio
            )
        )
    except Exception:
        return PermissionState.UNAVAILABLE

    # AVAuthorizationStatus: 0=NotDetermined, 1=Restricted, 2=Denied, 3=Authorized
    if status == 3:
        return PermissionState.GRANTED
    if status in (1, 2):
        return PermissionState.DENIED
    return PermissionState.NOT_DETERMINED


def request_microphone_permission(*, timeout_s: float = 30.0) -> PermissionState:
    """Explicitly request macOS microphone permission when triggered by the user."""
    current = check_microphone_permission()
    if current in (PermissionState.GRANTED, PermissionState.DENIED, PermissionState.UNAVAILABLE):
        return current

    try:
        import AVFoundation
    except Exception:
        return PermissionState.UNAVAILABLE

    done = threading.Event()
    granted_holder = [False]

    def _completion(granted: bool) -> None:
        granted_holder[0] = bool(granted)
        done.set()

    AVFoundation.AVCaptureDevice.requestAccessForMediaType_completionHandler_(
        AVFoundation.AVMediaTypeAudio, _completion
    )
    done.wait(timeout=timeout_s)
    if granted_holder[0]:
        return PermissionState.GRANTED
    return check_microphone_permission()
