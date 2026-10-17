#!/usr/bin/env python3
"""Native Devtool UI-D01 source-bound host gate, shared unchanged by GitHub Actions.

Writes only sanitized evidence; source hashes bind results to the exact changed files.
Never mutates an app, Steam, saved games, device state, or qualification receipts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/devtool/earthy_ui_source.py"
TEST = ROOT / "scripts/devtool/test_ui_earthy.py"
SOURCE_PATHS = (
    ".devtool.toml",
    "app/src/main/java/com/sdvsync/MainActivity.kt",
    "app/src/main/java/com/sdvsync/ui/theme/AppearancePreferences.kt",
    "app/src/main/java/com/sdvsync/ui/theme/EarthyColorSchemes.kt",
    "app/src/main/java/com/sdvsync/ui/theme/EarthyDesignTokens.kt",
    "app/src/main/java/com/sdvsync/ui/theme/EarthyPreview.kt",
    "app/src/main/java/com/sdvsync/ui/theme/Theme.kt",
    "app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt",
    "app/src/main/java/com/sdvsync/ui/components/StardewButton.kt",
    "app/src/main/java/com/sdvsync/ui/components/StardewBottomBar.kt",
    "app/src/main/java/com/sdvsync/ui/components/PixelProgressBar.kt",
    "scripts/devtool/earthy_ui_source.py",
    "scripts/devtool/test_ui_earthy.py",
    "scripts/devtool/ui_d01_gate.py",
    "docs/security/M3_RELEASE_POLICY.json",
)


def produce() -> dict:
    paths = {}
    for rel in SOURCE_PATHS:
        f = ROOT / rel
        if not f.is_file() or f.is_symlink():
            return {"schema_version": 1, "producer": "cinderbox-ui-d01-devtool", "overall": "BLOCKED_SOURCE_MISSING", "missing_path": rel, "release_qualified": False, "publication_allowed": False}
        paths[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
    source_proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True, timeout=30)
    source_doc = {}
    if source_proc.returncode == 0:
        try:
            source_doc = json.loads(source_proc.stdout)
        except (json.JSONDecodeError, ValueError):
            pass
    source_ok = source_proc.returncode == 0 and source_doc.get("overall") == "PASS_HOST_STATIC"
    test_proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "scripts/devtool", "-p", "test_ui_earthy.py", "-q"], cwd=ROOT, capture_output=True, text=True, timeout=90) if source_ok else None
    tests_ok = test_proc is not None and test_proc.returncode == 0
    check_count = sum(bool(v) for v in source_doc.get("checks", {}).values())
    return {
        "schema_version": 1,
        "producer": "cinderbox-ui-d01-devtool",
        "overall": "PASS_HOST_SOURCE" if (source_ok and tests_ok) else "FAILED_HOST_SOURCE",
        "source_commit": os.environ.get("GITHUB_SHA", ""),
        "source_sha256": paths,
        "source_checks_passed": check_count,
        "source_checks_total": len(source_doc.get("checks", {})),
        "contrast_ratios": source_doc.get("contrast_ratios", {}),
        "ui_host_tests": "PASS" if tests_ok else ("NOT_RUN" if test_proc is None else "FAILED"),
        "device_tests": "NOT_RUN",
        "android_build": "NOT_RUN",
        "historical_m21_results_replaced": False,
        "release_qualified": False,
        "publication_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Explicit receipt destination; defaults to JSON stdout")
    args = parser.parse_args()
    try:
        result = produce()
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        result = {"schema_version": 1, "producer": "cinderbox-ui-d01-devtool", "overall": "BLOCKED_HOST_GATE", "error_class": type(exc).__name__, "release_qualified": False, "publication_allowed": False}
    raw = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8")
    print(raw, end="")
    return 0 if result["overall"] == "PASS_HOST_SOURCE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
