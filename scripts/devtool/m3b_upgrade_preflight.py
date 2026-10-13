#!/usr/bin/env python3
"""Read-only device upgrade compatibility check (no install, no root, no data mutation).

Downloads the existing installed base APK into an auto-deleted temp directory to
compare its verified signing certificate with the candidate's certificate.
Requires an explicit authorized ADB serial; refuses ambiguous/offline devices.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from m3b_release_candidate import GateError, inspect_apk

PACKAGE = 'com.sdvsync'
SERIAL = re.compile(r'[A-Za-z0-9._:-]{1,128}\Z')
APK_PATH = re.compile(r'/[^\r\n\x00]+/base\.apk\Z')


def adb(serial: str, *parts: str, timeout: int = 30) -> str:
    p = subprocess.run(['adb', '-s', serial, *parts], text=True,
                       capture_output=True, timeout=timeout, check=False)
    if p.returncode != 0:
        raise GateError('ADB command failed; device state was not changed')
    return p.stdout.strip()


def preflight(serial: str, candidate: Path) -> str:
    if not SERIAL.fullmatch(serial):
        raise GateError('Invalid or missing explicit device serial')
    devices = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=20, check=False)
    if devices.returncode:
        raise GateError('Cannot list authorized ADB devices')
    active = [line.split()[0] for line in devices.stdout.splitlines()[1:]
              if len(line.split()) >= 2 and line.split()[1] == 'device']
    if serial not in active:
        raise GateError('Selected device is not authorized and online')
    sdk = adb(serial, 'shell', 'getprop', 'ro.build.version.sdk')
    if not sdk.isdecimal() or int(sdk) < 26:
        raise GateError('Android SDK is outside supported range')
    new = inspect_apk(candidate)
    packages = adb(serial, 'shell', 'pm', 'path', PACKAGE)
    if not packages:
        return f'NEW INSTALL ONLY: {PACKAGE} not installed; no upgrade compatibility proven (SDK {sdk})'
    paths = [line.removeprefix('package:') for line in packages.splitlines() if line.startswith('package:')]
    bases = [p for p in paths if APK_PATH.fullmatch(p)]
    if len(bases) != 1:
        raise GateError('Cannot establish exactly one installed base APK for certificate check')
    with tempfile.TemporaryDirectory(prefix='cinderbox-upgrade-') as td:
        installed_file = Path(td) / 'base.apk'
        adb(serial, 'pull', bases[0], str(installed_file), timeout=120)
        old = inspect_apk(installed_file)
    if old['certificate_sha256'] != new['certificate_sha256']:
        raise GateError('Signing mismatch: installing would not be a compatible in-place upgrade')
    if new['version_code'] < old['version_code']:
        raise GateError('Candidate versionCode would downgrade the installed app')
    return f'PREFLIGHT PASS: {PACKAGE} signing identity compatible, versionCode {old["version_code"]} -> {new["version_code"]}; NO APK INSTALLED'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--apk', required=True, type=Path)
    args = parser.parse_args()
    try:
        print(preflight(args.serial, args.apk))
    except (GateError, OSError, subprocess.TimeoutExpired) as exc:
        print(f'UPGRADE PREFLIGHT BLOCKED: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
