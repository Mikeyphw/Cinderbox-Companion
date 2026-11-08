#!/usr/bin/env python3
"""Fail-closed offline setup for disposable GitHub API36 Android emulators.

Use ConnectivityService's airplane-mode command, not ``mobile_data`` (a
persisted preference which may remain enabled when the modem/radio is off).
Both framework-level airplane-mode state and the absence of a default network
must be proved. Wi-Fi is independently disabled and verified, since Android
permits Wi-Fi to be enabled while airplane mode is on.
"""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
import time

SERIAL = 'emulator-5554'
DEFAULT = re.compile(r'(?m)^\s*Active default network:\s*(\S+)\s*$')


class OfflineRefusal(Exception):
    pass


def run_adb(serial: str, *args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(['adb', '-s', serial, *args], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OfflineRefusal('ADB_UNAVAILABLE') from exc


def checked(serial: str, *args: str) -> str:
    response = run_adb(serial, *args)
    if response.returncode != 0:
        raise OfflineRefusal('ADB_COMMAND_REFUSED')
    return response.stdout.decode('utf-8', 'replace').strip().replace('\r', '')


def ensure_offline(serial: str = SERIAL, *, polls: int = 12) -> str:
    if serial != SERIAL:
        raise OfflineRefusal('EMULATOR_SERIAL_REFUSED')
    if checked(serial, 'shell', 'getprop', 'ro.kernel.qemu') != '1':
        raise OfflineRefusal('PHYSICAL_DEVICE_REFUSED')
    if checked(serial, 'shell', 'getprop', 'ro.build.version.sdk') != '36':
        raise OfflineRefusal('ANDROID_API36_REQUIRED')

    # AOSP ConnectivityService owns the setting AND the radio-change
    # broadcast. Writing settings.global.airplane_mode_on alone is not enough.
    # If the command is missing or unauthorized, fail without qualifying CI.
    if run_adb(serial, 'shell', 'cmd', 'connectivity', 'airplane-mode', 'enable').returncode != 0:
        raise OfflineRefusal('AIRPLANE_ENABLE_REFUSED')

    # Airplane mode intentionally allows optional Wi-Fi on Android, so ensure
    # Wi-Fi is disabled independently and refuse any shutdown error.
    if run_adb(serial, 'shell', 'svc', 'wifi', 'disable').returncode != 0:
        raise OfflineRefusal('WIFI_SHUTDOWN_REFUSED')

    # Read back two independent views of airplane mode, not just the command's
    # return code; unknown or contradictory output must refuse qualification.
    if checked(serial, 'shell', 'cmd', 'connectivity', 'airplane-mode') != 'enabled':
        raise OfflineRefusal('AIRPLANE_NOT_ENABLED')
    if checked(serial, 'shell', 'settings', 'get', 'global', 'airplane_mode_on') != '1':
        raise OfflineRefusal('AIRPLANE_SETTING_NOT_ENABLED')
    if checked(serial, 'shell', 'settings', 'get', 'global', 'wifi_on') != '0':
        raise OfflineRefusal('WIFI_NOT_DISABLED')

    # No internet probe, packet generation, or private device data. Require
    # ConnectivityService to have no default network after teardown. An
    # unknown dumpsys shape fails rather than being mistaken for offline.
    attempts = max(1, min(int(polls), 20))
    for attempt in range(attempts):
        dump = checked(serial, 'shell', 'dumpsys', 'connectivity')
        match = DEFAULT.search(dump)
        if match is None:
            raise OfflineRefusal('DEFAULT_NETWORK_UNVERIFIABLE')
        if match.group(1).lower() in {'none', 'null'}:
            print('R48_OFFLINE_NETWORK_VERIFIED:AIRPLANE_MODE')
            return 'AIRPLANE_MODE'
        if attempt < attempts - 1:
            time.sleep(1)
    raise OfflineRefusal('ACTIVE_DEFAULT_NETWORK_REFUSED')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', default=SERIAL)
    args = parser.parse_args()
    try:
        ensure_offline(args.serial)
    except OfflineRefusal as exc:
        print('R48_OFFLINE_GATE_REFUSED:' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
