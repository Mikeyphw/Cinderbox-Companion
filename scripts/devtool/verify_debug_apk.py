#!/usr/bin/env python3
"""Fail closed if the assembled debug APK is absent or structurally invalid."""
from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path


def check_apk(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        if not path.is_file() or path.stat().st_size < 4096:
            return [f"APK missing or unreasonably small: {path}"]
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if "AndroidManifest.xml" not in names:
                errors.append("AndroidManifest.xml missing")
            if "classes.dex" not in names:
                errors.append("classes.dex missing")
            corrupt = archive.testzip()
            if corrupt:
                errors.append(f"Corrupt ZIP member: {corrupt}")
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        errors.append(f"Cannot read debug APK: {exc}")
    return errors


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    paths = sorted((repo / "app/build/outputs/apk/debug").glob("*.apk"))
    if not paths:
        print("DEBUG APK FAIL: no APK under app/build/outputs/apk/debug", file=sys.stderr)
        return 1
    for path in paths:
        failures = check_apk(path)
        for error in failures:
            print(f"DEBUG APK FAIL: {path.name}: {error}", file=sys.stderr)
        if failures:
            return 1
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"DEBUG APK OK: {path.name} size={path.stat().st_size} sha256={digest}")
    print("Structural checks only: no release-signing or source-reproducibility claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
