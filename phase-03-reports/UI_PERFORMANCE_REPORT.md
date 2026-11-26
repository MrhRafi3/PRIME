# PRIME Phase 03 UI Performance Report (Apple M1, 8 GB RAM)

**Measured Host:** MacBook Air M1 (`8,589,934,592` bytes / 8.0 GB unified memory), macOS `27.2.1` (`arm64`)  
**Runtime Stack:** Python `3.12.16` + `PySide6-Essentials 6.10.3` (`QQuickStyle("Basic")`)  

---

## 1. Measured Resource Footprint

Measured directly via `/usr/bin/time -l uv run prime ui --auto-close-ms 2500 --screenshot-path ...`:

| Metric | Observed Value | Assessment for M1 8 GB |
| :--- | :--- | :--- |
| **Peak Resident Set Size (RSS)** | **206,176,256 bytes (~196.6 MiB)** | Well within Phase 01 target (<250 MiB idle UI ceiling), leaving >5.5 GB headroom for future 3B–4B local LLM + STT |
| **OS Swaps** | **0 swaps** | Zero memory pressure or SSD swap triggered |
| **Total Wall Time (2.5s window run)** | **3.03 s** (~0.5s startup/teardown) | Sub-second cold startup |
| **CPU Time (2.5s active animated run)** | **1.06 s user + 0.61 s sys** | Low CPU load; `Canvas` repaints only when animated angles change |
| **PySide6 On-Disk Footprint** | **318 MB** (`PySide6-Essentials`) | ~130+ MB lighter than full `PySide6` with `QtWebEngine`/`Qt3D` |

---

## 2. Design Choices Supporting 8 GB M1 Efficiency

1. **Selected `PySide6-Essentials` instead of full `PySide6`:** Excludes unused `QtWebEngine`, `Qt3D`, `QtMultimedia`, and `QtCharts` binaries.
2. **Offloaded Telemetry Polling:** `MetricsWorker` runs `ps` / `vm_stat` / `pmset` on a background `QThread` every 2.5 seconds (`~15-20 ms` per poll) so the QML render loop never stutters.
3. **Restrained QML `Canvas` HUD:** Single-pass 2D vector arc rendering (`JarvisHud.qml`) with `running: hudRoot.visible` pauses animations automatically when hidden, avoiding `VISION-1.2`'s CPU-heavy 45 FPS software Gaussian blur pipeline.
4. **No Background Daemons or Resident AI Runtimes:** Zero background audio capture or model weights loaded in Phase 03.
