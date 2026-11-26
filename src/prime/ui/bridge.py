"""Qt signals/slots view-model bridge connecting PRIME core, MLX, and Voice to QML."""

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
from prime.security.tiers import PermissionState
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

    def finalize_streaming(self, fallback_notice: str = "") -> str:
        if self._streaming_row is None:
            return ""
        row = self._streaming_row
        self._streaming_row = None
        final_text = self._items[row]["text"].strip()
        if not final_text:
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
        return final_text

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


class VoiceWorker(QObject):
    """Dedicated background worker running offline Whisper STT off the Qt UI thread."""

    transcriptionFinished = Signal(str, str)
    sttLoadFinished = Signal(bool, str)

    def __init__(self, app: PrimeApp) -> None:
        super().__init__()
        self._app = app

    @Slot(str)
    def load_stt(self, slug: str) -> None:
        try:
            self._app.load_stt_model(slug or None)
            self.sttLoadFinished.emit(True, "")
        except Exception as exc:
            self.sttLoadFinished.emit(False, str(exc))

    @Slot()
    def stop_and_transcribe(self) -> None:
        try:
            result = self._app.stop_and_transcribe_voice()
            self.transcriptionFinished.emit(result.text, "")
        except Exception as exc:
            self.transcriptionFinished.emit("", str(exc))


class PrimeUIBridge(QObject):
    """Thread-safe QML bridge driving the PRIME JARVIS desktop interface."""

    stateChanged = Signal()
    clockChanged = Signal()
    metricsChanged = Signal()
    activationChanged = Signal()
    settingsChanged = Signal()
    runtimeChanged = Signal()
    voiceChanged = Signal()
    audioLevelChanged = Signal()
    doubleClapTriggered = Signal()
    requestMetricsRefresh = Signal()
    requestModelLoad = Signal(str)
    requestGeneration = Signal(str)
    requestTranscribe = Signal()
    requestSttLoad = Signal(str)

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
        self._mic_level = 0.0
        self._recording_elapsed_s = 0.0
        self._transcription_preview = ""
        self._voice_error = ""

        self._app.voice.set_level_callback(self._on_audio_level_from_thread)
        self._app.voice.set_double_clap_callback(self._on_double_clap_from_thread)
        self.doubleClapTriggered.connect(self._handle_double_clap_on_ui)

        self._app.events.subscribe("assistant.state_changed", self._on_backend_state_changed)
        self._app.events.subscribe("activation.changed", self._on_backend_activation_changed)
        self._app.events.subscribe("config.updated", self._on_backend_config_changed)
        self._app.events.subscribe("ai.runtime_changed", self._on_runtime_changed)
        self._app.events.subscribe("voice.status_changed", self._on_voice_event)
        self._app.events.subscribe("voice.permission_changed", self._on_voice_event)

        self._metrics_thread: QThread | None = None
        self._metrics_worker: MetricsWorker | None = None
        self._inference_thread: QThread | None = None
        self._inference_worker: InferenceWorker | None = None
        self._voice_thread: QThread | None = None
        self._voice_worker: VoiceWorker | None = None
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

        self._voice_thread = QThread(self)
        self._voice_worker = VoiceWorker(self._app)
        self._voice_worker.moveToThread(self._voice_thread)
        self.requestTranscribe.connect(self._voice_worker.stop_and_transcribe)
        self.requestSttLoad.connect(self._voice_worker.load_stt)
        self._voice_worker.transcriptionFinished.connect(self._on_transcription_finished)
        self._voice_worker.sttLoadFinished.connect(self._on_stt_load_finished)
        self._voice_thread.start()

    def shutdown(self) -> None:
        if self._clock_timer is not None:
            self._clock_timer.stop()
        if self._metrics_timer is not None:
            self._metrics_timer.stop()
        if self._voice_thread is not None:
            self._app.cancel_voice_recording()
            self._voice_thread.quit()
            self._voice_thread.wait(2000)
            self._voice_thread = None
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
        self._app.events.unsubscribe("voice.status_changed", self._on_voice_event)
        self._app.events.unsubscribe("voice.permission_changed", self._on_voice_event)

    # ---- Backend Event Callbacks ----
    def _on_backend_state_changed(self, _event: PrimeEvent) -> None:
        self.stateChanged.emit()
        self.voiceChanged.emit()

    def _on_backend_activation_changed(self, _event: PrimeEvent) -> None:
        self.activationChanged.emit()
        self.voiceChanged.emit()

    def _on_backend_config_changed(self, _event: PrimeEvent) -> None:
        self.settingsChanged.emit()
        self.activationChanged.emit()
        self.runtimeChanged.emit()
        self.voiceChanged.emit()

    def _on_runtime_changed(self, _event: PrimeEvent) -> None:
        self.runtimeChanged.emit()

    def _on_voice_event(self, _event: PrimeEvent) -> None:
        self.voiceChanged.emit()

    def _on_audio_level_from_thread(self, level: float, elapsed_s: float) -> None:
        self._mic_level = level
        self._recording_elapsed_s = elapsed_s
        self.audioLevelChanged.emit()

    def _on_double_clap_from_thread(self) -> None:
        self.doubleClapTriggered.emit()

    @Slot()
    def _handle_double_clap_on_ui(self) -> None:
        self._transcription_preview = "Double-clap confirmed — starting listening..."
        self.voiceChanged.emit()
        if not self._app.get_voice_snapshot().recording:
            self.startPushToTalk()

    @Slot(str)
    def _on_token_delta(self, delta: str) -> None:
        self._messages.append_streaming_delta(delta)

    @Slot(object)
    def _on_generation_finished(self, result: Any) -> None:
        self._generation_pending = False
        reply_text = self._messages.finalize_streaming(result.system_notice)
        self.runtimeChanged.emit()
        if (
            result.backend_connected
            and not result.cancelled
            and reply_text
            and self._app.config.voice.tts_enabled
        ):
            self._app.speak_reply(reply_text)
            self.voiceChanged.emit()

    @Slot(bool, str)
    def _on_model_load_finished(self, ok: bool, err: str) -> None:
        if not ok and err:
            self._messages.append_message("PRIME System", err, kind="notice")
        self.runtimeChanged.emit()

    @Slot(bool, str)
    def _on_stt_load_finished(self, ok: bool, err: str) -> None:
        if not ok and err:
            self._voice_error = err
            self._messages.append_message("PRIME Voice", err, kind="notice")
        else:
            self._voice_error = ""
        self.voiceChanged.emit()

    @Slot(str, str)
    def _on_transcription_finished(self, transcript: str, err: str) -> None:
        self._mic_level = 0.0
        self._recording_elapsed_s = 0.0
        self.audioLevelChanged.emit()

        if err:
            self._voice_error = err
            self._transcription_preview = ""
            self._messages.append_message("PRIME Voice", err, kind="notice")
            self.voiceChanged.emit()
            return

        cleaned = transcript.strip()
        if not cleaned:
            self._transcription_preview = "No speech detected (silence or cancelled)."
            self.voiceChanged.emit()
            return

        self._voice_error = ""
        self._transcription_preview = cleaned
        self.voiceChanged.emit()
        self.sendMessage(cleaned)

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
        if self._voice_error and self._app.state == AssistantState.IDLE:
            return "error"
        return self._app.state.value

    @Property(str, notify=stateChanged)
    def assistantStateLabel(self) -> str:
        if self._voice_error and self._app.state == AssistantState.IDLE:
            return "ERROR"
        labels = {
            AssistantState.IDLE: "IDLE",
            AssistantState.LISTENING: "LISTENING",
            AssistantState.TRANSCRIBING: "TRANSCRIBING",
            AssistantState.THINKING: "THINKING",
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
        return "100% LOCAL ONLY • NO CLOUD AI OR VOICE"

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
        vsnap = self._app.get_voice_snapshot()
        if vsnap.recording:
            return f"Recording ({self._recording_elapsed_s:.1f}s)"
        if vsnap.transcribing:
            return "Transcribing locally..."
        if vsnap.stt_model_available:
            return f"Ready ({self._app.config.activation.ptt_shortcut})"
        return "STT Model Missing"

    @Property(str, notify=settingsChanged)
    def pttShortcut(self) -> str:
        return self._app.config.activation.ptt_shortcut

    @Property(bool, notify=activationChanged)
    def doubleClapEnabled(self) -> bool:
        return self._app.get_activation_snapshot().double_clap_enabled

    @Property(bool, notify=voiceChanged)
    def doubleClapMonitoring(self) -> bool:
        return self._app.get_voice_snapshot().double_clap_monitoring

    @Property(str, notify=voiceChanged)
    def doubleClapStatusText(self) -> str:
        vsnap = self._app.get_voice_snapshot()
        if vsnap.double_clap_monitoring:
            return "MONITORING ACTIVE (Mic Live)"
        if vsnap.double_clap_enabled:
            return "Opted-In (Monitoring Paused)"
        return "Disabled (Default)"

    @Property(float, notify=audioLevelChanged)
    def micLevel(self) -> float:
        return self._mic_level

    @Property(str, notify=audioLevelChanged)
    def recordingDurationText(self) -> str:
        return f"{self._recording_elapsed_s:.1f}s"

    @Property(bool, notify=voiceChanged)
    def isRecording(self) -> bool:
        return self._app.get_voice_snapshot().recording

    @Property(bool, notify=voiceChanged)
    def isTranscribing(self) -> bool:
        return self._app.get_voice_snapshot().transcribing or (
            self._app.state == AssistantState.TRANSCRIBING
        )

    @Property(bool, notify=voiceChanged)
    def isSpeaking(self) -> bool:
        return self._app.get_voice_snapshot().speaking or (
            self._app.state == AssistantState.SPEAKING
        )

    @Property(str, notify=voiceChanged)
    def micPermissionText(self) -> str:
        perm = self._app.get_voice_snapshot().mic_permission
        if perm == PermissionState.GRANTED:
            return "Granted"
        if perm == PermissionState.DENIED:
            return "Denied"
        if perm == PermissionState.NOT_DETERMINED:
            return "Not Requested"
        return "Unavailable"

    @Property(bool, notify=voiceChanged)
    def sttLoaded(self) -> bool:
        return self._app.get_voice_snapshot().stt_loaded

    @Property(bool, notify=voiceChanged)
    def sttModelAvailable(self) -> bool:
        return self._app.get_voice_snapshot().stt_model_available

    @Property(str, notify=settingsChanged)
    def sttModelSlug(self) -> str:
        return self._app.config.voice.stt_model_slug

    @Property(bool, notify=settingsChanged)
    def ttsEnabled(self) -> bool:
        return self._app.config.voice.tts_enabled

    @Property(str, notify=settingsChanged)
    def ttsEnglishVoice(self) -> str:
        return self._app.config.voice.tts_english_voice

    @Property(float, notify=settingsChanged)
    def ttsRate(self) -> float:
        return self._app.config.voice.tts_rate

    @Property(float, notify=settingsChanged)
    def ttsVolume(self) -> float:
        return self._app.config.voice.tts_volume

    @Property(str, notify=voiceChanged)
    def transcriptionPreview(self) -> str:
        return self._transcription_preview

    @Property(str, notify=voiceChanged)
    def voiceErrorText(self) -> str:
        return self._voice_error

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
    def startPushToTalk(self) -> None:
        self._voice_error = ""
        try:
            self._app.start_voice_recording(allow_prompt=True)
            self._transcription_preview = "Listening locally (zero audio saved to disk)..."
        except Exception as exc:
            self._voice_error = str(exc)
            self._messages.append_message("PRIME Voice", str(exc), kind="notice")
        self.voiceChanged.emit()

    @Slot()
    def releasePushToTalk(self) -> None:
        if not self._app.get_voice_snapshot().recording:
            return
        self._transcription_preview = "Transcribing offline with Whisper..."
        self.voiceChanged.emit()
        if self._voice_thread is not None and self._voice_thread.isRunning():
            self.requestTranscribe.emit()
            return
        try:
            res = self._app.stop_and_transcribe_voice()
            self._on_transcription_finished(res.text, "")
        except Exception as exc:
            self._on_transcription_finished("", str(exc))

    @Slot()
    def cancelVoiceInput(self) -> None:
        self._app.cancel_voice_recording()
        self._mic_level = 0.0
        self._recording_elapsed_s = 0.0
        self._transcription_preview = "Voice input cancelled."
        self.audioLevelChanged.emit()
        self.voiceChanged.emit()

    @Slot()
    def stopSpeaking(self) -> None:
        self._app.stop_speaking()
        self.voiceChanged.emit()

    @Slot()
    def loadSttModel(self) -> None:
        slug = self._app.config.voice.stt_model_slug
        if self._voice_thread is not None and self._voice_thread.isRunning():
            self.requestSttLoad.emit(slug)
            return
        try:
            self._app.load_stt_model(slug)
        except Exception as exc:
            self._voice_error = str(exc)
            self._messages.append_message("PRIME Voice", str(exc), kind="notice")
        self.voiceChanged.emit()

    @Slot()
    def unloadSttModel(self) -> None:
        self._app.unload_stt_model()
        self.voiceChanged.emit()

    @Slot()
    def toggleDoubleClapMonitoring(self) -> None:
        self._voice_error = ""
        current = self._app.get_voice_snapshot().double_clap_monitoring
        try:
            self._app.set_double_clap_monitoring(not current, allow_prompt=True)
        except Exception as exc:
            self._voice_error = str(exc)
            self._messages.append_message("PRIME Voice", str(exc), kind="notice")
        self.voiceChanged.emit()

    @Slot()
    def requestMicrophonePermission(self) -> None:
        self._app.request_microphone_access()
        self.voiceChanged.emit()

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
        if self._app.get_voice_snapshot().recording:
            self.releasePushToTalk()
        else:
            self.startPushToTalk()

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

    @Slot(str, str, bool, str, str, bool, str, float, float)
    def saveAllPreferences(
        self,
        language_mode: str,
        memory_profile: str,
        double_clap_enabled: bool,
        model_slug: str,
        stt_model_slug: str,
        tts_enabled: bool,
        tts_english_voice: str,
        tts_rate: float,
        tts_volume: float,
    ) -> None:
        self._app.update_settings(
            language_mode=LanguageMode(language_mode),
            memory_profile=MemoryProfile(memory_profile),
            double_clap_enabled=double_clap_enabled,
            selected_model_slug=model_slug,
            stt_model_slug=stt_model_slug,
            tts_enabled=tts_enabled,
            tts_english_voice=tts_english_voice,
            tts_rate=tts_rate,
            tts_volume=tts_volume,
            persist=True,
        )

    @Slot()
    def clearConversationView(self) -> None:
        self._messages.clear()
