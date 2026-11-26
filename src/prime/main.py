"""CLI entry point for PRIME foundation diagnostics and status."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from prime import APP_NAME, BUNDLE_ID, __version__
from prime.config.settings import ConfigError, load_config
from prime.core.app import PrimeApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prime",
        description=f"{APP_NAME} ({BUNDLE_ID}) — Local-first personal AI assistant foundation",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional path to a local TOML/JSON configuration file.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Initialize foundation modules and print runtime status.")
    sub.add_parser("config", help="Print validated sanitized configuration as JSON.")
    sub.add_parser("doctor", help="Run non-invasive environment and hardware readiness checks.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        config = load_config(config_path=args.config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.command == "config":
        print(json.dumps(config.to_safe_dict(), indent=2))
        return 0

    app = PrimeApp(config)
    try:
        snap = app.bootstrap()
        if args.command == "status":
            print(json.dumps(asdict(snap), indent=2))
            return 0
        if args.command == "doctor":
            sys_info = app.system.get_system_info()
            batt = app.system.get_battery_status()
            report = {
                "status": asdict(snap),
                "system": {
                    "platform": sys_info.platform.value,
                    "os_version": sys_info.os_version,
                    "arch": sys_info.machine_arch,
                    "cpu": sys_info.cpu_brand,
                    "ram_gb": round(sys_info.total_memory_bytes / (1024**3), 2),
                },
                "battery": asdict(batt),
            }
            print(json.dumps(report, indent=2))
            return 0
    finally:
        app.shutdown()

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
