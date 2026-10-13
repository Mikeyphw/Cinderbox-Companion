#!/usr/bin/env python3
"""Explicit non-mutating Android device probe; NOT proof tests passed.

No root requests, APK installs, logcat, saved-game access, or device IDs in output.
Use `./devtoolw device` separately for the real instrumentation job.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


def adb(*args: str) -> str:
    process = subprocess.run(["adb", *args], capture_output=True, text=True,
                             timeout=20, check=False)
    if process.returncode:
        raise RuntimeError("ADB probe failed; no device evidence was produced")
    return process.stdout.strip()


def capture(root: Path) -> dict:
    if shutil.which("adb") is None:
        raise RuntimeError("adb is not on PATH")
    devices = [line.split()[0] for line in adb("devices").splitlines()[1:]
               if len(line.split()) >= 2 and line.split()[1] == "device"]
    if len(devices) != 1:
        raise RuntimeError("Exactly one authorized ADB device is required")
    serial = devices[0]
    sdk = adb("-s", serial, "shell", "getprop", "ro.build.version.sdk")
    release = adb("-s", serial, "shell", "getprop", "ro.build.version.release")
    abi = adb("-s", serial, "shell", "getprop", "ro.product.cpu.abi")
    if not re.fullmatch(r"\d{2,3}", sdk) or not release or not abi:
        raise RuntimeError("ADB did not return valid Android platform data")
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    return {
        "schema_version": 1, "kind": "device-preflight-only",
        "source_commit": head,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "android_sdk": int(sdk), "android_release": release, "abi": abi,
        "adb_authorized": True,
        "instrumentation_passed": False, "manual_gameplay_passed": False,
        "release_qualified": False,
        "note": "Device IDs, paths, and app data are intentionally not captured. Run Devtool device tests separately."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; use a new file to preserve prior evidence")
    try:
        result = capture(args.root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("Device preflight recorded (instrumentation NOT run):", args.output)
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        print(f"DEVICE PREFLIGHT FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
