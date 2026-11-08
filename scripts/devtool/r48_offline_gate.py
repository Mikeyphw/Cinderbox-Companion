#!/usr/bin/env python3
"""Fail-closed, account-free network gate for disposable GitHub API36 emulators.

Telephony-less emulator images may omit the ``phone`` binder service; that is
not a failure to shut down an available cellular radio. A default network or
unknown radio/connectivity state still refuses hosted acceptance.
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
    # Never ignore Wi-Fi shutdown errors.
    if run_adb(serial, 'shell', 'svc', 'wifi', 'disable').returncode != 0:
        raise OfflineRefusal('WIFI_SHUTDOWN_REFUSED')
    # Prefer attempting mobile shutdown. Only a specifically absent phone
    # service on the verified emulator permits skipping cellular shutdown.
    data = run_adb(serial, 'shell', 'svc', 'data', 'disable')
    if data.returncode == 0:
        cellular = 'CELLULAR_DISABLED'
    else:
        phone = run_adb(serial, 'shell', 'service', 'check', 'phone')
        response = (phone.stdout + b'\n' + phone.stderr).decode('utf-8', 'replace').strip()
        if phone.returncode != 0 or response != 'Service phone: not found':
            raise OfflineRefusal('CELLULAR_SHUTDOWN_REFUSED')
        cellular = 'TELEPHONY_ABSENT'
    if checked(serial, 'shell', 'settings', 'get', 'global', 'wifi_on') != '0':
        raise OfflineRefusal('WIFI_NOT_DISABLED')
    if cellular == 'CELLULAR_DISABLED':
        mobile_setting = checked(serial, 'shell', 'settings', 'get', 'global', 'mobile_data')
        if mobile_setting != '0':
            # On some API36 system images ``svc data disable`` exits 0 even
            # though no phone service exists; the global setting can remain
            # stale. Require independent, exact service absence, then still
            # prove there is no active default network below.
            phone = run_adb(serial, 'shell', 'service', 'check', 'phone')
            response = (phone.stdout + b'\n' + phone.stderr).decode('utf-8', 'replace').strip()
            if phone.returncode != 0 or response != 'Service phone: not found':
                raise OfflineRefusal('CELLULAR_NOT_DISABLED')
            cellular = 'TELEPHONY_ABSENT'
    # AOSP ConnectivityService reports 'Active default network: none' when
    # getDefaultNetwork() is null; no direct internet requests or private data.
    # Poll briefly for framework teardown after disabling the radios. Unknown
    # output must NEVER be treated as equivalent to an offline network.
    for attempt in range(max(1, min(int(polls), 20))):
        dump = checked(serial, 'shell', 'dumpsys', 'connectivity')
        match = DEFAULT.search(dump)
        if match is None:
            raise OfflineRefusal('DEFAULT_NETWORK_UNVERIFIABLE')
        if match.group(1).lower() in {'none', 'null'}:
            print('R48_OFFLINE_NETWORK_VERIFIED:' + cellular)
            return cellular
        if attempt < polls - 1:
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
