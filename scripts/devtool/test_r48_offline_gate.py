#!/usr/bin/env python3
"""Deterministic negative and positive fixtures for R48A network qualification."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r48_offline_gate as gate


class FakeADB:
    def __init__(self, *, data_ok=False, phone='Service phone: not found', wifi='0',
                 default='none', wifi_command_ok=True, cellular_setting='0',
                 sdk='36', qemu='1', dumpsys_ok=True, shutdown_rc=20):
        self.data_ok = data_ok
        self.phone = phone
        self.wifi = wifi
        self.default = default
        self.wifi_command_ok = wifi_command_ok
        self.cellular_setting = cellular_setting
        self.sdk = sdk
        self.qemu = qemu
        self.dumpsys_ok = dumpsys_ok
        self.shutdown_rc = shutdown_rc
        self.calls = []

    def __call__(self, command, **_kwargs):
        self.calls.append(command)
        key = tuple(command[3:])
        rc, stdout = 0, b''
        if key == ('shell', 'getprop', 'ro.kernel.qemu'):
            stdout = self.qemu.encode()
        elif key == ('shell', 'getprop', 'ro.build.version.sdk'):
            stdout = self.sdk.encode()
        elif key == ('shell', 'svc', 'wifi', 'disable'):
            rc = 0 if self.wifi_command_ok else 1
        elif key == ('shell', 'svc', 'data', 'disable'):
            rc = 0 if self.data_ok else self.shutdown_rc
        elif key == ('shell', 'service', 'check', 'phone'):
            stdout = self.phone.encode()
        elif key == ('shell', 'settings', 'get', 'global', 'wifi_on'):
            stdout = self.wifi.encode()
        elif key == ('shell', 'settings', 'get', 'global', 'mobile_data'):
            stdout = self.cellular_setting.encode()
        elif key == ('shell', 'dumpsys', 'connectivity'):
            rc = 0 if self.dumpsys_ok else 1
            stdout = ('NetworkProviders for:\nActive default network: ' + self.default + '\nCurrent Networks:\n').encode()
        else:
            raise AssertionError(f'unexpected ADB call: {key}')
        return subprocess.CompletedProcess(command, rc, stdout, b'')


class OfflineGateTests(unittest.TestCase):
    def qualify(self, fake, serial=gate.SERIAL, polls=1):
        with patch.object(gate.subprocess, 'run', side_effect=fake), patch.object(gate.time, 'sleep'):
            return gate.ensure_offline(serial, polls=polls)

    def refuse(self, fake, reason, serial=gate.SERIAL):
        with self.assertRaisesRegex(gate.OfflineRefusal, reason):
            self.qualify(fake, serial)

    def test_no_phone_service_emulator_succeeds_after_wifi_and_network_verified(self):
        fake=FakeADB()
        self.assertEqual('TELEPHONY_ABSENT', self.qualify(fake))
        self.assertIn(['adb','-s',gate.SERIAL,'shell','service','check','phone'], fake.calls)
        self.assertIn(['adb','-s',gate.SERIAL,'shell','dumpsys','connectivity'], fake.calls)

    def test_valid_telephony_radio_shuts_down_normally(self):
        fake=FakeADB(data_ok=True)
        self.assertEqual('CELLULAR_DISABLED', self.qualify(fake))
        self.assertNotIn(['adb','-s',gate.SERIAL,'shell','service','check','phone'],fake.calls)
        self.assertIn(['adb','-s',gate.SERIAL,'shell','settings','get','global','mobile_data'],fake.calls)

    def test_successful_noop_data_command_requires_explicit_absent_phone(self):
        # API36 hosted emulator: svc data succeeds but mobile_data stays 1.
        fake = FakeADB(data_ok=True, cellular_setting='1', phone='Service phone: not found')
        self.assertEqual('TELEPHONY_ABSENT', self.qualify(fake))
        self.assertIn(['adb', '-s', gate.SERIAL, 'shell', 'service', 'check', 'phone'], fake.calls)
        self.assertIn(['adb', '-s', gate.SERIAL, 'shell', 'dumpsys', 'connectivity'], fake.calls)

    def test_successful_data_command_with_live_phone_and_stale_setting_refuses(self):
        self.refuse(FakeADB(data_ok=True, cellular_setting='1',
                            phone='Service phone: found'), 'CELLULAR_NOT_DISABLED')

    def test_successful_data_command_with_unknown_phone_identity_refuses(self):
        self.refuse(FakeADB(data_ok=True, cellular_setting='null',
                            phone='Service phone: unavailable'), 'CELLULAR_NOT_DISABLED')

    def test_noop_data_with_no_phone_but_active_default_network_refuses(self):
        self.refuse(FakeADB(data_ok=True, cellular_setting='1', default='101'),
                    'ACTIVE_DEFAULT_NETWORK_REFUSED')

    def test_noop_data_with_no_phone_but_wifi_still_on_refuses(self):
        self.refuse(FakeADB(data_ok=True, cellular_setting='1', wifi='1'),
                    'WIFI_NOT_DISABLED')

    def test_cellular_shutdown_fails_when_phone_service_exists(self):
        self.refuse(FakeADB(phone='Service phone: found'), 'CELLULAR_SHUTDOWN_REFUSED')

    def test_unknown_telephony_failure_is_not_skipped(self):
        self.refuse(FakeADB(phone='Service phone: unavailable'), 'CELLULAR_SHUTDOWN_REFUSED')

    def test_failed_wifi_shutdown_is_fatal(self):
        self.refuse(FakeADB(wifi_command_ok=False), 'WIFI_SHUTDOWN_REFUSED')

    def test_wifi_must_really_be_off(self):
        self.refuse(FakeADB(wifi='1'), 'WIFI_NOT_DISABLED')

    def test_cellular_setting_must_be_off_if_service_available(self):
        self.refuse(FakeADB(data_ok=True, cellular_setting='1', phone='Service phone: found'),
                    'CELLULAR_NOT_DISABLED')

    def test_active_default_network_is_never_qualified(self):
        self.refuse(FakeADB(default='101'), 'ACTIVE_DEFAULT_NETWORK_REFUSED')

    def test_unknown_connectivity_output_refused(self):
        self.refuse(FakeADB(default=''), 'DEFAULT_NETWORK_UNVERIFIABLE')

    def test_unreadable_connectivity_refused(self):
        self.refuse(FakeADB(dumpsys_ok=False), 'ADB_COMMAND_REFUSED')

    def test_physical_device_identity_refused(self):
        self.refuse(FakeADB(qemu=''), 'PHYSICAL_DEVICE_REFUSED')

    def test_non_api36_refused(self):
        self.refuse(FakeADB(sdk='35'), 'ANDROID_API36_REQUIRED')

    def test_other_serial_refused_before_any_adb_call(self):
        fake=FakeADB()
        self.refuse(fake, 'EMULATOR_SERIAL_REFUSED', 'localhost:5555')
        self.assertEqual([],fake.calls)

    def test_null_default_network_accepted_if_other_gates_pass(self):
        self.assertEqual('TELEPHONY_ABSENT', self.qualify(FakeADB(default='null')))

    def test_network_tear_down_may_be_polled(self):
        fake=FakeADB()
        count=[0]
        def run(sequence, **kwargs):
            if sequence[-2:] == ['dumpsys', 'connectivity']:
                count[0]+=1
                fake.default = '102' if count[0] < 3 else 'none'
            return fake(sequence,**kwargs)
        with patch.object(gate.subprocess,'run',side_effect=run),patch.object(gate.time,'sleep') as sleep:
            self.assertEqual('TELEPHONY_ABSENT',gate.ensure_offline(polls=3))
            self.assertEqual(2,sleep.call_count)

    def test_never_performs_network_probes_or_service_changes_outside_radio_controls(self):
        fake=FakeADB()
        self.qualify(fake)
        args=' '.join(' '.join(x) for x in fake.calls)
        for forbidden in ('curl','ping','http://','https://','install','pm clear','/sdcard','connect Steam'):
            self.assertNotIn(forbidden,args)


if __name__ == '__main__':
    unittest.main(verbosity=2)
