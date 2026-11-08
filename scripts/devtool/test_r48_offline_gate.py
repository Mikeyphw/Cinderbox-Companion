#!/usr/bin/env python3
"""Deterministic success, failure and state-fidelity tests for R48A offline CI."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r48_offline_gate as gate


class FakeADB:
    def __init__(self, *, airplane_command_ok=True, airplane_query='enabled',
                 airplane_setting='1', wifi_command_ok=True, wifi_setting='0',
                 default='none', sdk='36', qemu='1', dumpsys_ok=True,
                 airplane_query_ok=True, settings_ok=True, mobile_setting='1'):
        self.airplane_command_ok = airplane_command_ok
        self.airplane_query = airplane_query
        self.airplane_query_ok = airplane_query_ok
        self.airplane_setting = airplane_setting
        self.wifi_command_ok = wifi_command_ok
        self.wifi_setting = wifi_setting
        self.default = default
        self.sdk = sdk
        self.qemu = qemu
        self.dumpsys_ok = dumpsys_ok
        self.settings_ok = settings_ok
        # Deliberately stale on actual API36 emulators; should never be queried.
        self.mobile_setting = mobile_setting
        self.calls = []

    def __call__(self, command, **_kwargs):
        self.calls.append(command)
        key = tuple(command[3:])
        rc, stdout, stderr = 0, b'', b''
        if key == ('shell', 'getprop', 'ro.kernel.qemu'):
            stdout = self.qemu.encode()
        elif key == ('shell', 'getprop', 'ro.build.version.sdk'):
            stdout = self.sdk.encode()
        elif key == ('shell', 'cmd', 'connectivity', 'airplane-mode', 'enable'):
            rc = 0 if self.airplane_command_ok else 20
            if rc: stderr = b'cmd: ConnectivityService unavailable'
        elif key == ('shell', 'cmd', 'connectivity', 'airplane-mode'):
            rc = 0 if self.airplane_query_ok else 20
            stdout = self.airplane_query.encode()
        elif key == ('shell', 'svc', 'wifi', 'disable'):
            rc = 0 if self.wifi_command_ok else 1
        elif key == ('shell', 'settings', 'get', 'global', 'airplane_mode_on'):
            rc = 0 if self.settings_ok else 1
            stdout = self.airplane_setting.encode()
        elif key == ('shell', 'settings', 'get', 'global', 'wifi_on'):
            rc = 0 if self.settings_ok else 1
            stdout = self.wifi_setting.encode()
        elif key == ('shell', 'dumpsys', 'connectivity'):
            rc = 0 if self.dumpsys_ok else 1
            stdout = ('NetworkProviders for:\nActive default network: ' + self.default +
                      '\nCurrent Networks:\n').encode()
        else:
            raise AssertionError(f'unexpected ADB call: {key}')
        return subprocess.CompletedProcess(command, rc, stdout, stderr)


class OfflineGateTests(unittest.TestCase):
    def qualify(self, fake, *, serial=gate.SERIAL, polls=1):
        with patch.object(gate.subprocess, 'run', side_effect=fake), patch.object(gate.time, 'sleep'):
            return gate.ensure_offline(serial, polls=polls)

    def refuse(self, fake, reason, *, serial=gate.SERIAL):
        with self.assertRaisesRegex(gate.OfflineRefusal, reason):
            self.qualify(fake, serial=serial)

    def test_real_api36_stale_mobile_preference_is_not_a_radio_status(self):
        fake = FakeADB(mobile_setting='1')
        self.assertEqual('AIRPLANE_MODE', self.qualify(fake))
        self.assertFalse(any('mobile_data' in str(c) for c in fake.calls))

    def test_correct_airplane_mode_wifi_and_default_network_are_all_checked(self):
        fake = FakeADB()
        self.assertEqual('AIRPLANE_MODE', self.qualify(fake))
        self.assertEqual([('cmd', 'connectivity', 'airplane-mode', 'enable'),
                          ('svc', 'wifi', 'disable'),
                          ('cmd', 'connectivity', 'airplane-mode'),
                          ('settings', 'get', 'global', 'airplane_mode_on'),
                          ('settings', 'get', 'global', 'wifi_on'),
                          ('dumpsys', 'connectivity')],
                         [tuple(c[4:]) for c in fake.calls[2:]])

    def test_command_failure_is_not_ignored(self):
        self.refuse(FakeADB(airplane_command_ok=False), 'AIRPLANE_ENABLE_REFUSED')

    def test_command_failure_prevents_wifi_or_any_later_actions(self):
        fake = FakeADB(airplane_command_ok=False)
        self.refuse(fake, 'AIRPLANE_ENABLE_REFUSED')
        self.assertEqual(3, len(fake.calls))

    def test_readback_disabled_is_refused(self):
        self.refuse(FakeADB(airplane_query='disabled'), 'AIRPLANE_NOT_ENABLED')

    def test_readback_unknown_is_refused(self):
        self.refuse(FakeADB(airplane_query='unavailable'), 'AIRPLANE_NOT_ENABLED')

    def test_readback_error_is_refused(self):
        self.refuse(FakeADB(airplane_query_ok=False), 'ADB_COMMAND_REFUSED')

    def test_airplane_setting_zero_refused(self):
        self.refuse(FakeADB(airplane_setting='0'), 'AIRPLANE_SETTING_NOT_ENABLED')

    def test_airplane_setting_unknown_refused(self):
        self.refuse(FakeADB(airplane_setting='null'), 'AIRPLANE_SETTING_NOT_ENABLED')

    def test_airplane_setting_read_failure_refused(self):
        self.refuse(FakeADB(settings_ok=False), 'ADB_COMMAND_REFUSED')

    def test_wifi_shutdown_failure_refused(self):
        self.refuse(FakeADB(wifi_command_ok=False), 'WIFI_SHUTDOWN_REFUSED')

    def test_wifi_still_on_even_in_airplane_mode_refused(self):
        self.refuse(FakeADB(wifi_setting='1'), 'WIFI_NOT_DISABLED')

    def test_wifi_setting_unknown_refused(self):
        self.refuse(FakeADB(wifi_setting='null'), 'WIFI_NOT_DISABLED')

    def test_active_default_network_even_in_airplane_mode_refused(self):
        self.refuse(FakeADB(default='102'), 'ACTIVE_DEFAULT_NETWORK_REFUSED')

    def test_unknown_default_network_refused(self):
        self.refuse(FakeADB(default=''), 'DEFAULT_NETWORK_UNVERIFIABLE')

    def test_unreadable_connectivity_refused(self):
        self.refuse(FakeADB(dumpsys_ok=False), 'ADB_COMMAND_REFUSED')

    def test_no_default_network_reported_as_null_accepted(self):
        self.assertEqual('AIRPLANE_MODE', self.qualify(FakeADB(default='null')))

    def test_no_default_network_reported_as_none_accepted(self):
        self.assertEqual('AIRPLANE_MODE', self.qualify(FakeADB(default='none')))

    def test_physical_device_refused(self):
        self.refuse(FakeADB(qemu=''), 'PHYSICAL_DEVICE_REFUSED')

    def test_old_android_api_refused(self):
        self.refuse(FakeADB(sdk='35'), 'ANDROID_API36_REQUIRED')

    def test_wrong_serial_refused_before_any_adb(self):
        fake = FakeADB()
        self.refuse(fake, 'EMULATOR_SERIAL_REFUSED', serial='localhost:5555')
        self.assertFalse(fake.calls)

    def test_network_teardown_is_polled(self):
        fake = FakeADB()
        counter = [0]
        def run(sequence, **kwargs):
            if sequence[-2:] == ['dumpsys', 'connectivity']:
                counter[0] += 1
                fake.default = '101' if counter[0] < 3 else 'none'
            return fake(sequence, **kwargs)
        with patch.object(gate.subprocess, 'run', side_effect=run), patch.object(gate.time, 'sleep') as sleep:
            self.assertEqual('AIRPLANE_MODE', gate.ensure_offline(polls=3))
            self.assertEqual(2, sleep.call_count)

    def test_zero_polls_still_checks_once(self):
        fake = FakeADB(default='101')
        self.refuse(fake, 'ACTIVE_DEFAULT_NETWORK_REFUSED')
        with patch.object(gate.subprocess, 'run', side_effect=fake), patch.object(gate.time, 'sleep') as sleep:
            with self.assertRaises(gate.OfflineRefusal): gate.ensure_offline(polls=0)
            sleep.assert_not_called()

    def test_no_network_probes_or_unauthorized_radio_mutations(self):
        fake = FakeADB()
        self.qualify(fake)
        args = ' '.join(' '.join(c) for c in fake.calls)
        for forbidden in ('curl', 'ping', 'http://', 'https://', 'pm clear', 'install',
                          '/sdcard', 'svc data', 'mobile_data', 'service check phone'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, args)

    def test_main_prints_bounded_error_code_not_adb_output(self):
        with patch('sys.argv', ['r48_offline_gate.py', '--serial', 'wrong']):
            self.assertEqual(1, gate.main())


if __name__ == '__main__':
    unittest.main(verbosity=2)
