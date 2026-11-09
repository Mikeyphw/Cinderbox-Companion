#!/usr/bin/env python3
"""CB-NX01 Q01 privacy and fail-closed physical acceptance contract tests."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import cbnx01_physical_acceptance as q


def baseline():
    return {'installed_base_apk_sha256': 'a'*64,
            'mods_directory_listing_sha256': 'b'*64,
            'firefox_packages_present': ['org.mozilla.firefox'],
            'pending_review': {'present': False}}


class AcceptanceTests(unittest.TestCase):
    def test_real_staging_is_observation_not_false_qualification(self):
        before = baseline()
        after = copy.deepcopy(before)
        after['pending_review'] = {'present': True, 'archive_sha256': 'c'*64,
                                   'archive_bytes': 200, 'source': 'nexus', 'mod_id': '123'}
        result = q.assess(before, after, '123', '456')
        self.assertEqual(result['failure_codes'], [])
        self.assertEqual(result['status'], 'STAGING_OBSERVED_NOT_FULLY_QUALIFIED')
        self.assertFalse(result['exact_file_binary_provenance_verified'])
        self.assertFalse(result['firefox_to_android_handoff_acknowledged_by_app'])
        self.assertFalse(result['live_nexus_end_to_end_qualified'])
        self.assertFalse(result['release_qualified'])
        self.assertNotIn('nxm://', json.dumps(result))

    def test_wrong_mod_and_mutated_mods_refused(self):
        before = baseline()
        after = copy.deepcopy(before)
        after['mods_directory_listing_sha256'] = 'd'*64
        after['pending_review'] = {'present': True, 'archive_sha256': 'c'*64,
                                   'archive_bytes': 200, 'source': 'nexus', 'mod_id': '999'}
        self.assertIn('STAGED_MOD_ID_MISMATCH', q.assess(before, after, '123','456')['failure_codes'])
        self.assertIn('MODS_LISTING_CHANGED_BEFORE_APPROVAL', q.assess(before, after, '123','456')['failure_codes'])

    def test_no_new_archive_and_changed_apk_refused(self):
        before = baseline()
        after = copy.deepcopy(before)
        after['installed_base_apk_sha256'] = 'd'*64
        reasons = q.assess(before, after, '123','456')['failure_codes']
        self.assertIn('NO_ARCHIVE_STAGED', reasons)
        self.assertIn('INSTALLED_APK_CHANGED', reasons)

    def test_preexisting_review_never_passes(self):
        before = baseline()
        before['pending_review'] = {'present': True}
        reasons = q.assess(before, before, '123', '456')['failure_codes']
        self.assertIn('PREEXISTING_PENDING_REVIEW', reasons)

    def test_secret_output_never_contains_raw_adb_bytes(self):
        class FakeAdb:
            def call(self, *args, optional=False):
                if args[:2] == ('shell','ls'):
                    return b'private-mod-name nonce-secret\n'
                return None
        listing = FakeAdb().call('shell','ls')
        self.assertNotIn('private-mod-name', json.dumps({'inventory': q.digest(listing)}))
        self.assertTrue(q.HEX64.fullmatch(q.digest(listing)))

    def test_serial_and_positive_ids_strict(self):
        for bad in ['emulator-5554','12345','user.net:5555','127.0.0.1:1']:
            with self.assertRaises(q.Refusal): q.Adb(bad)
        for bad in ['', '0','-1','abc','1?x=3','9999999999999']:
            self.assertFalse(q.ID.fullmatch(bad))

    def test_private_output_exclusive_and_restrictive(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'evidence'/'before.json'
            q.write_private(p, {'status': 'NOT_QUALIFIED'})
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                q.write_private(p, {})

    def test_device_probe_refuses_emulator(self):
        class FakeAdb:
            def text(self, *args, **kwargs):
                return {('get-state',): 'device',
                        ('shell','getprop','ro.build.version.sdk'): '36',
                        ('shell','getprop','ro.kernel.qemu'): '1',
                        ('shell','getprop','ro.product.cpu.abi'): 'arm64-v8a'}[args]
        with self.assertRaisesRegex(q.Refusal, 'PHYSICAL_ARM64_ANDROID36_REQUIRED'):
            q.physical_snapshot(FakeAdb())

    def test_no_remote_urls_or_credentials_in_source(self):
        src = Path(q.__file__).read_text()
        self.assertNotIn('curl ', src)
        self.assertNotIn('https://api.nexusmods.com', src)
        self.assertNotIn('adb root', src)
        self.assertNotIn('setprop', src)


if __name__ == '__main__': unittest.main()
