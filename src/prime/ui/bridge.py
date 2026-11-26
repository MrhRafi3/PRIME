"""Qt signals/slots view-model bridge connecting PRIME core and MLX runtime to QML."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    QThread,
    QTimer,
    Signal,
    Slot,
)

from prime.config.settings import LanguageMode, MemoryProfile
from prime.core.app import PrimeApp
from prime.core.events import AssistantState, PrimeEvent
from prime.intelligence.runtime.manager import RuntimeState
from prime.system.base import SystemMetrics

_INVALID_INDEX = QModelIndex()


class MessageListModel(QAbstractListModel):
    """Lightweight list model exposing conversation and streaming entries safely to QML."""

    RoleRole = Qt.ItemDataRole.UserRole + 1
    TextRole = Qt.ItemDataRole.UserRole + 2
    TimeRole = Qt.ItemDataRole.UserRole + 3
    KindRole = Qt.ItemDataRole.UserRole + 4

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[dict[str, str]] = []
        self._streaming_row: int | None = None

    def rowCount(self, parent: QModelIndex = _INVALID_INDEX) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role == self.RoleRole:
            return item["role"]
        if role == self.TextRole:
            return item["text"]
        if role == self.TimeRole:
            return item["timestamp"]
        if role == self.KindRole:
            return item["kind"]
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.RoleRole: b"msgRole",
            self.TextRole: b"msgText",
            self.TimeRole: b"msgTime",
            self.KindRole: b"msgKind",
        }

    def append_message(self, role: str, text: str, *, kind: str = "normal") -> int:
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(
            {
                "role": role,
                "text": text,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "kind": kind,
            }
        )
        self.endInsertRows()
        return row

    def begin_streaming_assistant(self) -> int:
        self._streaming_row = self.append_message("PRIME", "", kind="assistant")
        return self._streaming_row

    def append_streaming_delta(self, delta: str) -> None:
        if self._streaming_row is None or not delta:
            return
        row = self._streaming_row
        self._items[row]["text"] += delta
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [self.TextRole])

    def finalize_streaming(self, fallback_notice: str = "") -> None:
        if self._streaming_row is None:
            return
        row = self._streaming_row
        self._streaming_row = None
        if not self._items[row]["text"].strip():
            if fallback_notice:
                self._items[row]["role"] = "PRIME System"
                self._items[row]["text"] = fallback_notice
                self._items[row]["kind"] = "notice"
                idx = self.index(row, 0)
                self.dataChanged.emit(idx, idx, [self.RoleRole, self.TextRole, self.KindRole])
            else:
                self.beginRemoveRows(QModelIndex(), row, row)
                self._items.pop(row)
                self.endRemoveRows()

    def clear(self) -> None:
        self._streaming_row = None
        if not self._items:
            return
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()


class MetricsWorker(QObject):
    """Background worker collecting SystemMetrics off the Qt UI thread."""

    metricsReady = Signal(object)

    def __init__(self, app: PrimeApp) -> None:
        super().__init__()
        self._app = app

    @Slot()
    def collect(self) -> None:
        try:
            metrics = self._app.system.get_system_metrics()
        except Exception:
            metrics = SystemMetrics(
                cpu_percent=None,
                memory_used_gb=None,
                memory_total_gb=None,
                memory_percent=None,
                battery_percent=None,
                battery_charging=None,
            )
        self.metricsReady.emit(metrics)


class InferenceWorker(QObject):
    """Dedicated background worker running MLX model load and token streaming off UI thread."""

    tokenDelta = Signal(str)
    generationFinished = Signal(object)
    modelLoadFinished = Signal(bool, str)

    def __init__(self, app: PrimeApp) -> None:
        super().__init__()
        self._app = app

    @Slot(str)
    def load_model(self, slug: str) -> None:
        try:
            self._app.load_local_model(slug or None)
            self.modelLoadFinished.emit(True, "")
        except Exception as exc:
            self.modelLoadFinished.emit(False, str(exc))

    @Slot(str)
    def generate_for_text(self, text: str) -> None:
        result = self._app.submit_text_message(
            text,
            on_token=lambda delta, _chunk: self.tokenDelta.emit(delta),
        )
        self.generationFinished.emit(result)


class PrimeUIBridge(QObject):
    """Thread-safe QML bridge driving the PRIME JARVIS desktop interface."""

    stateChanged = Signal()
    clockChanged = Signal()
    metricsChanged = Signal()
    activationChanged = Signal()
    settingsChanged = Signal()
    runtimeChanged = Signal()
    requestMetricsRefresh = Signal()
    requestModelLoad = Signal(str)
    requestGeneration = Signal(str)

    def __init__(
        self,
        prime_app: PrimeApp,
        *,
        start_timers: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._app = prime_app
        self._messages = MessageListModel(self)
        self._current_time = datetime.now().strftime("%H:%M:%S")
        self._current_date = datetime.now().strftime("%a, %d %b %Y")
        self._cpu_text = "Sampling..."
        self._memory_text = "Sampling..."
        self._battery_text = "Sampling..."
        self._cpu_ratio = 0.0
        self._memory_ratio = 0.0
        self._generation_pending = False

        self._app.events.subscribe("assistant.state_changed", self._on_backend_state_changed)
        self._app.events.subscribe("activation.changed", self._on_backend_activation_changed)
        self._app.events.subscribe("config.updated", self._on_backend_config_changed)
        self._app.events.subscribe("ai.runtime_changed", self._on_runtime_changed)

        self._metrics_thread: QThread | None = None
        self._metrics_worker: MetricsWorker | None = None
        self._inference_thread: QThread | None = None
        self._inference_worker: InferenceWorker | None = None
        self._clock_timer: QTimer | None = None
        self._metrics_timer: QTimer | None = None

        if start_timers:
            self._init_background_workers()
            self._clock_timer = QTimer(self)
            self._clock_timer.setInterval(1000)
            self._clock_timer.timeout.connect(self._tick_clock)
            self._clock_timer.start()

            self._metrics_timer = QTimer(self)
            self._metrics_timer.setInterval(2500)
            self._metrics_timer.timeout.connect(self.refresh_metrics)
            self._metrics_timer.start()
            QTimer.singleShot(50, self.refresh_metrics)

    def _init_background_workers(self) -> None:
        self._metrics_thread = QThread(self)
        self._metrics_worker = MetricsWorker(self._app)
        self._metrics_worker.moveToThread(self._metrics_thread)
        self.requestMetricsRefresh.connect(self._metrics_worker.collect)
        self._metrics_worker.metricsReady.connect(self.apply_metrics)
        self._metrics_thread.start()

        self._inference_thread = QThread(self)
        self._inference_worker = InferenceWorker(self._app)
        self._inference_worker.moveToThread(self._inference_thread)
        self.requestModelLoad.connect(self._inference_worker.load_model)
        self.requestGeneration.connect(self._inference_worker.generate_for_text)
        self._inference_worker.tokenDelta.connect(self._on_token_delta)
        self._inference_worker.generationFinished.connect(self._on_generation_finished)
        self._inference_worker.modelLoadFinished.connect(self._on_model_load_finished)
        self._inference_thread.start()

    def shutdown(self) -> None:
        if self._clock_timer is not None:
            self._clock_timer.stop()
        if self._metrics_timer is not None:
            self._metrics_timer.stop()
        if self._inference_thread is not None:
            self._app.cancel_generation()
            self._inference_thread.quit()
            self._inference_thread.wait(2000)
            self._inference_thread = None
        if self._metrics_thread is not None:
            self._metrics_thread.quit()
            self._metrics_thread.wait(1500)
            self._metrics_thread = None
        self._app.events.unsubscribe("assistant.state_changed", self._on_backend_state_changed)
        self._app.events.unsubscribe("activation.changed", self._on_backend_activation_changed)
        self._app.events.unsubscribe("config.updated", self._on_backend_config_changed)
        self._app.events.unsubscribe("ai.runtime_changed", self._on_runtime_changed)

    # ---- Backend Event Callbacks ----
    def _on_backend_state_changed(self, _event: PrimeEvent) -> None:
        self.stateChanged.emit()

    def _on_backend_activation_changed(self, _event: PrimeEvent) -> None:
        self.activationChanged.emit()

    def _on_backend_config_changed(self, _event: PrimeEvent) -> None:
        self.settingsChanged.emit()
        self.activationChanged.emit()
        self.runtimeChanged.emit()

    def _on_runtime_changed(self, _event: PrimeEvent) -> None:
        self.runtimeChanged.emit()

    @Slot(str)
    def _on_token_delta(self, delta: str) -> None:
        self._messages.append_streaming_delta(delta)

    @Slot(object)
    def _on_generation_finished(self, result: Any) -> None:
        self._generation_pending = False
        if result.backend_connected:
            self._messages.finalize_streaming(result.system_notice)
        else:
            self._messages.finalize_streaming(result.system_notice)
        self.runtimeChanged.emit()

    @Slot(bool, str)
    def _on_model_load_finished(self, ok: bool, err: str) -> None:
        if not ok and err:
            self._messages.append_message("PRIME System", err, kind="notice")
        self.runtimeChanged.emit()

    def _tick_clock(self) -> None:
        now = datetime.now()
        self._current_time = now.strftime("%H:%M:%S")
        self._current_date = now.strftime("%a, %d %b %Y")
        self.clockChanged.emit()

    @Slot()
    def refresh_metrics(self) -> None:
        if self._metrics_thread is not None and self._metrics_thread.isRunning():
            self.requestMetricsRefresh.emit()

    @Slot(object)
    def apply_metrics(self, metrics: SystemMetrics) -> None:
        if metrics.cpu_percent is None:
            self._cpu_text = "Unavailable"
            self._cpu_ratio = 0.0
        else:
            self._cpu_text = f"{metrics.cpu_percent:.1f}%"
            self._cpu_ratio = max(0.0, min(1.0, metrics.cpu_percent / 100.0))

        if (
            metrics.memory_used_gb is None
            or metrics.memory_total_gb is None
            or metrics.memory_percent is None
        ):
            self._memory_text = "Unavailable"
            self._memory_ratio = 0.0
        else:
            self._memory_text = (
                f"{metrics.memory_used_gb:.2f} / {metrics.memory_total_gb:.0f} GB "
                f"({metrics.memory_percent:.0f}%)"
            )
            self._memory_ratio = max(0.0, min(1.0, metrics.memory_percent / 100.0))

        if metrics.battery_percent is None:
            self._battery_text = "Unavailable"
        else:
            charge_label = (
                "Charging"
                if metrics.battery_charging is True
                else ("On Battery" if metrics.battery_charging is False else "Power Unknown")
            )
            self._battery_text = f"{metrics.battery_percent}% • {charge_label}"

        self.metricsChanged.emit()

    # ---- Read-Only Properties for QML ----
    @Property(str, constant=True)
    def appName(self) -> str:
        return self._app.config.identity.app_name

    @Property(str, constant=True)
    def bundleId(self) -> str:
        return self._app.config.identity.bundle_id

    @Property(str, constant=True)
    def versionText(self) -> str:
        return f"v{self._app.config.identity.version}"

    @Property(str, notify=stateChanged)
    def assistantState(self) -> str:
        return self._app.state.value

    @Property(str, notify=stateChanged)
    def assistantStateLabel(self) -> str:
        labels = {
            AssistantState.IDLE: "IDLE",
            AssistantState.LISTENING: "LISTENING",
            AssistantState.THINKING: "PROCESSING",
            AssistantState.SPEAKING: "SPEAKING",
            AssistantState.STARTING: "STARTING",
            AssistantState.SHUTTING_DOWN: "SHUTTING DOWN",
            AssistantState.STOPPED: "OFFLINE",
        }
        return labels.get(self._app.state, self._app.state.value.upper())

    @Property(bool, notify=runtimeChanged)
    def aiBackendConnected(self) -> bool:
        return self._app.ai_backend_connected

    @Property(str, notify=runtimeChanged)
    def runtimeStateText(self) -> str:
        return self._app.get_runtime_snapshot().state.value

    @Property(str, notify=runtimeChanged)
    def activeModelName(self) -> str:
        return self._app.get_runtime_snapshot().active_model_name

    @Property(str, notify=runtimeChanged)
    def selectedModelSlug(self) -> str:
        return self._app.get_runtime_snapshot().selected_model_slug

    @Property(bool, notify=runtimeChanged)
    def isModelAvailable(self) -> bool:
        snap = self._app.get_runtime_snapshot()
        return snap.state != RuntimeState.MODEL_NOT_INSTALLED

    @Property(bool, notify=runtimeChanged)
    def isGenerating(self) -> bool:
        if self._generation_pending:
            return True
        snap = self._app.get_runtime_snapshot()
        return snap.state in {
            RuntimeState.THINKING,
            RuntimeState.STREAMING_RESPONSE,
            RuntimeState.CANCELLING,
        }

    @Property(str, notify=runtimeChanged)
    def tokensPerSecText(self) -> str:
        snap = self._app.get_runtime_snapshot()
        if snap.tokens_per_sec <= 0:
            return "-- tok/s"
        return f"{snap.tokens_per_sec:.1f} tok/s"

    @Property(int, notify=runtimeChanged)
    def lastTokenCount(self) -> int:
        return self._app.get_runtime_snapshot().last_token_count

    @Property(str, notify=runtimeChanged)
    def runtimeErrorText(self) -> str:
        return self._app.get_runtime_snapshot().error_message

    @Property(str, notify=runtimeChanged)
    def backendStatusText(self) -> str:
        snap = self._app.get_runtime_snapshot()
        if self._app.ai_backend_connected:
            return f"Core Active • MLX: {snap.state.value} ({snap.active_model_name})"
        return f"Core Active • {snap.state.value}"

    @Property(str, constant=True)
    def localPrivacyText(self) -> str:
        return "100% LOCAL ONLY • NO CLOUD AI"

    @Property(str, notify=clockChanged)
    def currentTimeText(self) -> str:
        return self._current_time

    @Property(str, notify=clockChanged)
    def currentDateText(self) -> str:
        return self._current_date

    @Property(str, notify=metricsChanged)
    def cpuText(self) -> str:
        return self._cpu_text

    @Property(float, notify=metricsChanged)
    def cpuRatio(self) -> float:
        return self._cpu_ratio

    @Property(str, notify=metricsChanged)
    def memoryText(self) -> str:
        return self._memory_text

    @Property(float, notify=metricsChanged)
    def memoryRatio(self) -> float:
        return self._memory_ratio

    @Property(str, notify=metricsChanged)
    def batteryText(self) -> str:
        return self._battery_text

    @Property(bool, notify=activationChanged)
    def pushToTalkPressed(self) -> bool:
        return self._app.get_activation_snapshot().push_to_talk_pressed

    @Property(str, notify=activationChanged)
    def pushToTalkStatusText(self) -> str:
        snap = self._app.get_activation_snapshot()
        if snap.push_to_talk_pressed:
            return "Active (UI Only — Mic Not Accessed)"
        if not self._app.config.activation.push_to_talk_enabled:
            return "Disabled"
        return "Configured • Audio Deferred (Phase 05)"

    @Property(bool, notify=activationChanged)
    def doubleClapEnabled(self) -> bool:
        return self._app.get_activation_snapshot().double_clap_enabled

    @Property(str, notify=activationChanged)
    def doubleClapStatusText(self) -> str:
        snap = self._app.get_activation_snapshot()
        if snap.double_clap_enabled:
            return "Configured • Audio Inactive (Phase 05)"
        return "Disabled"

    @Property(str, notify=settingsChanged)
    def languageMode(self) -> str:
        return self._app.config.ai.language_mode.value

    @Property(str, notify=settingsChanged)
    def memoryProfile(self) -> str:
        return self._app.config.ai.memory_profile.value

    @Property(QObject, constant=True)
    def messagesModel(self) -> MessageListModel:
        return self._messages

    # ---- Slots Invoked by QML ----
    @Slot(str)
    def sendMessage(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned or self._generation_pending:
            return
        self._messages.append_message("You", cleaned, kind="user")
        if self._app.ai_backend_connected and self._inference_thread is not None:
            self._generation_pending = True
            self._messages.begin_streaming_assistant()
            self.runtimeChanged.emit()
            self.requestGeneration.emit(cleaned)
            return

        result = self._app.submit_text_message(cleaned)
        if not result.backend_connected and result.system_notice:
            self._messages.append_message("PRIME System", result.system_notice, kind="notice")
        elif result.assistant_text:
            self._messages.append_message("PRIME", result.assistant_text, kind="assistant")

    @Slot()
    def loadModel(self) -> None:
        slug = self._app.config.ai.selected_model_slug
        if self._inference_thread is not None and self._inference_thread.isRunning():
            self.requestModelLoad.emit(slug)
            return
        try:
            self._app.load_local_model(slug)
        except Exception as exc:
            self._messages.append_message("PRIME System", str(exc), kind="notice")
        self.runtimeChanged.emit()

    @Slot()
    def unloadModel(self) -> None:
        self._app.unload_local_model()
        self.runtimeChanged.emit()

    @Slot()
    def cancelGeneration(self) -> None:
        self._app.cancel_generation()
        self.runtimeChanged.emit()

    @Slot(bool)
    def setPushToTalkPressed(self, pressed: bool) -> None:
        self._app.set_push_to_talk(pressed)

    @Slot()
    def togglePushToTalk(self) -> None:
        current = self._app.get_activation_snapshot().push_to_talk_pressed
        self._app.set_push_to_talk(not current)

    @Slot(bool)
    def setDoubleClapEnabled(self, enabled: bool) -> None:
        self._app.update_settings(double_clap_enabled=enabled, persist=True)

    @Slot(str, str, bool)
    def savePreferences(
        self, language_mode: str, memory_profile: str, double_clap_enabled: bool
    ) -> None:
        self._app.update_settings(
            language_mode=LanguageMode(language_mode),
            memory_profile=MemoryProfile(memory_profile),
            double_clap_enabled=double_clap_enabled,
            persist=True,
        )

    @Slot(str, str, bool, str)
    def saveModelAndPreferences(
        self,
        language_mode: str,
        memory_profile: str,
        double_clap_enabled: bool,
        model_slug: str,
    ) -> None:
        self._app.update_settings(
            language_mode=LanguageMode(language_mode),
            memory_profile=MemoryProfile(memory_profile),
            double_clap_enabled=double_clap_enabled,
            selected_model_slug=model_slug,
            persist=True,
        )

    @Slot()
    def clearConversationView(self) -> None:
        self._messages.clear()
