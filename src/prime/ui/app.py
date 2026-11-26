"""PySide6 application lifecycle runner for the PRIME desktop UI."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from prime.config.settings import PrimeConfig
from prime.core.app import PrimeApp
from prime.ui.bridge import PrimeUIBridge


def launch_ui(
    config: PrimeConfig,
    *,
    auto_close_ms: int = 0,
    screenshot_path: Path | None = None,
) -> int:
    """Launch the PRIME Qt Quick/QML desktop UI and manage clean shutdown."""
    prime_app = PrimeApp(config)
    prime_app.bootstrap()

    qt_app = QGuiApplication.instance()
    owns_qt_app = qt_app is None
    if qt_app is None:
        qt_app = QGuiApplication(sys.argv[:1])
    QQuickStyle.setStyle("Basic")
    qt_app.setApplicationName(config.identity.app_name)
    qt_app.setOrganizationName(config.identity.owner)
    qt_app.setApplicationVersion(config.identity.version)

    bridge = PrimeUIBridge(prime_app)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("primeBridge", bridge)

    qml_path = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    if not engine.rootObjects():
        bridge.shutdown()
        prime_app.shutdown()
        return 1

    root_window = engine.rootObjects()[0]

    def _capture_and_maybe_close() -> None:
        if screenshot_path is not None:
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            image = root_window.grabWindow()
            image.save(str(screenshot_path), "PNG")
        if auto_close_ms > 0:
            qt_app.quit()

    if screenshot_path is not None:
        delay = max(400, auto_close_ms - 150) if auto_close_ms > 0 else 800
        QTimer.singleShot(delay, _capture_and_maybe_close)
    elif auto_close_ms > 0:
        QTimer.singleShot(auto_close_ms, qt_app.quit)

    exit_code = 0
    try:
        if owns_qt_app:
            exit_code = qt_app.exec()
    finally:
        for obj in engine.rootObjects():
            obj.close()
        qt_app.processEvents()
        del engine
        bridge.shutdown()
        prime_app.shutdown()

    return int(exit_code)
