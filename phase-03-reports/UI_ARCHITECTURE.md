# PRIME UI Architecture (Phase 03)

## 1. Design Goals

- **Clean Separation:** All Qt/QML presentation code lives strictly inside `src/prime/ui/`, completely decoupled from `prime.core`, `prime.security`, `prime.intelligence`, and `prime.system`.
- **Lazy Qt Loading:** `PySide6` is imported only when `prime ui` or `prime.ui` is invoked, keeping headless CLI commands (`prime status`, `prime config`, `prime doctor`) fast and dependency-light.
- **Responsive UI Thread:** System telemetry collection (`ps`, `sysctl`, `vm_stat`, `pmset`) runs inside `MetricsWorker` on a dedicated background `QThread`, pushing immutable `SystemMetrics` snapshots to `PrimeUIBridge` via queued Qt signals.
- **Zero Fabricated AI Responses:** `PrimeApp.submit_text_message()` persists the user prompt locally in SQLite and emits a truthful `backend_connected=False` notice when no LLM provider is loaded.

---

## 2. Component Structure

```
src/prime/ui/
├── __init__.py
├── app.py                  # QGuiApplication + QQuickStyle("Basic") + QQmlApplicationEngine lifecycle
├── bridge.py               # PrimeUIBridge(QObject), MessageListModel(QAbstractListModel), MetricsWorker(QObject)
└── qml/
    ├── Main.qml            # 6-region JARVIS HUD layout (Header, HUD, Activation, Metrics, Chat, Footer)
    ├── JarvisHud.qml       # Restrained animated Canvas arc/core visualizer reactive to assistantState
    └── SettingsDialog.qml  # Local TOML persistence for double-clap config, bn-en/en language, M1 RAM profile
```

---

## 3. Event & Signal Data Flow

1. **User Action -> Backend:**
   - QML calls `@Slot` methods on `primeBridge` (`sendMessage`, `togglePushToTalk`, `setPushToTalkPressed`, `savePreferences`).
   - `PrimeUIBridge` delegates to `PrimeApp` (`submit_text_message`, `set_push_to_talk`, `update_settings`).
2. **Backend Events -> UI:**
   - `PrimeApp.events` (`EventBus`) publishes `"assistant.state_changed"`, `"activation.changed"`, and `"config.updated"`.
   - `PrimeUIBridge` translates these into Qt signals (`stateChanged`, `activationChanged`, `settingsChanged`), updating QML bindings reactively.
3. **Background Telemetry -> UI:**
   - A 2.5-second `QTimer` emits `requestMetricsRefresh` to `MetricsWorker.collect()` on `QThread`.
   - `MetricsWorker` calls `PrimeApp.system.get_system_metrics()` (Tier 0 read-only `MacOSSystemController`) and emits `metricsReady(SystemMetrics)` back to `PrimeUIBridge.apply_metrics()`.

---

## 4. Backend Extensions Made in Phase 03

- `prime.system.base.SystemMetrics` + `MacOSSystemController.get_system_metrics()`: Added lightweight stdlib-only CPU, memory, and battery telemetry with graceful `None` fallbacks.
- `prime.config.settings.save_config_toml()`: Added atomic `0700`/`0600` TOML persistence for non-sensitive UI preferences.
- `prime.voice.contracts.ActivationSnapshot` / `ActivationStatus`: Added UI-facing activation state models explicitly tracking `microphone_permission_requested=False`.
- `prime.core.app.PrimeApp`: Added `submit_text_message()`, `set_push_to_talk()`, and `update_settings()`.
