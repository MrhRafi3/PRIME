"""Non-invasive local environment diagnostic script for PRIME Phase 02."""

from __future__ import annotations

import platform
import sqlite3
import sys

from prime import APP_NAME, BUNDLE_ID, __version__


def main() -> int:
    info = {
        "app": APP_NAME,
        "bundle_id": BUNDLE_ID,
        "version": __version__,
        "python_version": platform.python_version(),
        "machine": platform.machine(),
        "sys_platform": sys.platform,
        "sqlite_version": sqlite3.sqlite_version,
    }
    for k, v in info.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
