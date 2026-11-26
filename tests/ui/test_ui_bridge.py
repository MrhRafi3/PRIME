"""UI and QML integration tests for PRIME Phase 03 desktop interface."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from prime.config import LanguageMode, MemoryProfile, load_config
from prime.core import AssistantState, PrimeApp
from prime.system.base import SystemMetrics
from prime.ui.bridge import PrimeUIBridge


def _get_qt_app() -> QGuiApplication:
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    app = QGuiApplication(["prime-test"])
    QQuickStyle.setStyle("Basic")
    return app


@pytest.mark.ui
def test_qml_main_loads_and_bridges_state(tmp_path: Path) -> None:
    qt_app = _get_qt_app()
    cfg = load_config(
        env={
            "PRIME_DATA_DIR": str(tmp_path / "data"),
            "PRIME_LOG_DIR": str(tmp_path / "logs"),
            "PRIME_ENVIRONMENT": "test",
        }
    )
    prime_app = PrimeApp(cfg, platform_override="darwin")
    prime_app.bootstrap()
    bridge = PrimeUIBridge(prime_app, start_timers=False)

    engine = QQmlApplicationEngine()
    warnings: list[str] = []
    engine.warnings.connect(lambda errs: warnings.extend(e.toString() for e in errs))
    engine.rootContext().setContextProperty("primeBridge", bridge)

    qml_path = Path(__file__).resolve().parents[2] / "src" / "prime" / "ui" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    qt_app.processEvents()

    try:
        assert len(engine.rootObjects()) == 1
        assert warnings == []
        assert bridge.appName == "PRIME"
        assert bridge.aiBackendConnected is False
        assert bridge.assistantState == AssistantState.IDLE.value
        assert bridge.localPrivacyText == "100% LOCAL ONLY • NO CLOUD AI OR VOICE"
    finally:
        for obj in engine.rootObjects():
            obj.close()
        qt_app.processEvents()
        del engine
        bridge.shutdown()
        prime_app.shutdown()


@pytest.mark.ui
def test_ui_bridge_activation_unavailable_ai_metrics_and_persistence(tmp_path: Path) -> None:
    _get_qt_app()
    cfg_path = tmp_path / "data" / "config.toml"
    cfg = load_config(
        env={
            "PRIME_DATA_DIR": str(tmp_path / "data"),
            "PRIME_LOG_DIR": str(tmp_path / "logs"),
            "PRIME_ENVIRONMENT": "test",
        }
    )
    prime_app = PrimeApp(cfg, platform_override="darwin")
    prime_app.bootstrap()
    bridge = PrimeUIBridge(prime_app, start_timers=False)

    try:
        # 1. Push-to-talk transitions cleanly without hardware recording or mic prompt
        bridge.setPushToTalkPressed(True)
        assert bridge.pushToTalkPressed is True
        assert bridge.assistantState == AssistantState.LISTENING.value
        assert prime_app.get_activation_snapshot().microphone_permission_requested is False

        bridge.setPushToTalkPressed(False)
        assert bridge.pushToTalkPressed is False
        assert bridge.assistantState == AssistantState.IDLE.value

        # 2. Sending a message when AI backend is offline never fabricates AI replies
        bridge.sendMessage("Amar nam Rafi, status ki?")
        assert bridge.messagesModel.rowCount() == 2
        idx_user = bridge.messagesModel.index(0, 0)
        idx_notice = bridge.messagesModel.index(1, 0)
        assert bridge.messagesModel.data(idx_user, bridge.messagesModel.RoleRole) == "You"
        assert (
            bridge.messagesModel.data(idx_notice, bridge.messagesModel.RoleRole) == "PRIME System"
        )
        assert bridge.messagesModel.data(idx_notice, bridge.messagesModel.KindRole) == "notice"
        assert prime_app.active_conversation_id is not None
        saved_msgs = prime_app.memory.get_messages(prime_app.active_conversation_id)
        assert len(saved_msgs) == 1
        assert saved_msgs[0].role == "user"

        # 3. Missing metrics handled gracefully
        bridge.apply_metrics(SystemMetrics(None, None, None, None, None, None))
        assert bridge.cpuText == "Unavailable"
        assert bridge.memoryText == "Unavailable"
        assert bridge.batteryText == "Unavailable"
        assert bridge.cpuRatio == 0.0
        assert bridge.memoryRatio == 0.0

        # 4. Settings persistence round-trip
        bridge.savePreferences("en", "eco", False)
        assert bridge.languageMode == "en"
        assert bridge.memoryProfile == "eco"
        assert bridge.doubleClapEnabled is False

        reloaded = load_config(config_path=cfg_path, env={})
        assert reloaded.ai.language_mode == LanguageMode.ENGLISH
        assert reloaded.ai.memory_profile == MemoryProfile.ECO
        assert reloaded.activation.double_clap_enabled is False
    finally:
        bridge.shutdown()
        prime_app.shutdown()
