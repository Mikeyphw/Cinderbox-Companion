#!/usr/bin/env python3
"""Offline regression gate for Cinderbox M0/M1 security guarantees.

This is a narrow source-level invariant check, not a replacement for testing,
APK analysis, or a security audit. Does not invoke `su` or require Android.
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree as ET


ANDROID = "{http://schemas.android.com/apk/res/android}"


def check(repo: Path) -> list[str]:
    failures: list[str] = []
    manifest = repo / "app/src/main/AndroidManifest.xml"
    root_source = repo / "app/src/main/java/com/sdvsync/fileaccess/RootFileAccess.kt"
    detector_source = repo / "app/src/main/java/com/sdvsync/fileaccess/FileAccessDetector.kt"
    try:
        application = ET.parse(manifest).getroot().find("application")
        if application is None:
            failures.append("AndroidManifest.xml has no <application>")
        else:
            for key, expected in (("usesCleartextTraffic", "false"), ("allowBackup", "false")):
                actual = application.get(ANDROID + key)
                if actual != expected:
                    failures.append(f"AndroidManifest.xml: android:{key} should be {expected}; got {actual!r}")
    except (ET.ParseError, OSError) as exc:
        failures.append(f"Cannot parse AndroidManifest.xml: {exc}")

    try:
        root = root_source.read_text(encoding="utf-8")
        if "PrivilegedSavePaths.requireAllowed(" not in root or "PrivilegedSavePaths.requireChild(" not in root:
            failures.append("Root operations must validate against the allowed save paths")
        if "RootShell.quote(" not in root:
            failures.append("Root shell calls must shell-quote dynamic paths")
    except OSError as exc:
        failures.append(f"Cannot read RootFileAccess.kt: {exc}")

    try:
        detector = detector_source.read_text(encoding="utf-8")
        start = detector.index("fun detectBestStrategy()")
        tail = detector.index("fun resolveStrategy()", start)
        auto = detector[start:tail]
        if "RootFileAccess.isAvailable()" in auto or "return RootFileAccess()" in auto:
            failures.append("Automatic file-access selection must never probe or select root")
        if "isRootExplicitlyEnabled()" not in detector:
            failures.append("Explicit user opt-in for root is required")
    except (OSError, ValueError) as exc:
        failures.append(f"Cannot check FileAccessDetector.kt: {exc}")
    return failures


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    failures = check(repo)
    for failure in failures:
        print(f"SECURITY CONTRACT FAIL: {failure}", file=sys.stderr)
    if failures:
        return 1
    print("Cinderbox M0/M1 security source contract: OK (static only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
