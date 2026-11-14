#!/usr/bin/env python3
"""LAB06 strict offline positives, negatives and no-physical-claim contracts."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from cbnx06_lab06_readiness import (
    CASES, SCHEMA, Refused, load_hosted, report, review_hosted, write_new,
)

A = 'a' * 40
B = 'b' * 40


def hosted():
    return {
        'schema': 'cbnx06-lab05-ui-api36-v1', 'status': 'PASS',
        'source_sha': A, 'run_id': '12345', 'apk_sha256': 'c' * 64,
        'test_apk_sha256': 'd' * 64, 'actual_test_count': 4, 'tests_passed': 4,
        'cases': [dict(case=x, status='PASS', reason='NONE', site='NONE',
                       failure_category='NONE') for x in CASES],
        'emulator_only': True, 'physical_qualified': False,
        'live_iceraven_qualified': False, 'nexus_file_provenance_verified': False,
        'production_game_unchanged_proven': False, 'release_qualified': False,
    }


class ReadinessTests(unittest.TestCase):
    def check_refuse(self, mutate, pattern):
        h = hosted()
        mutate(h)
        with self.assertRaisesRegex(Refused, pattern):
            report(A, B, h)

    def test_deferred_by_default(self):
        v = report(A, B)
        self.assertEqual(v['schema'], SCHEMA)
        self.assertFalse(v['hosted_ui_api36_pass_source_bound'])
        self.assertEqual(v['physical_read_only_acceptance'], 'DEFERRED')
        self.assertTrue(v['no_adb_or_device_actions_performed'])
        self.assertFalse(v['release_qualified'])

    def test_source_bound_hosted_receipt_remains_physical_unqualified(self):
        v = report(A, B, hosted())
        self.assertTrue(v['hosted_ui_api36_pass_source_bound'])
        self.assertFalse(v['hosted_receipt_authenticity_independently_verified'])
        self.assertFalse(v['github_workflow_conclusion_verified_by_this_tool'])
        self.assertEqual(v['hosted_ui_run_id'], '12345')
        for k in ('physical_qualified', 'live_iceraven_qualified',
                  'production_game_unchanged_proven', 'release_qualified'):
            self.assertFalse(v[k])

    def test_bad_android_sha(self):
        with self.assertRaisesRegex(Refused, 'ANDROID_SOURCE_SHA_INVALID'): report('short', B)

    def test_bad_browser_sha(self):
        with self.assertRaisesRegex(Refused, 'BROWSER_SOURCE_SHA_INVALID'): report(A, B.upper())

    def test_reject_stale_hosted_source(self):
        self.check_refuse(lambda h: h.update(source_sha=B), 'HOSTED_SOURCE_MISMATCH')

    def test_reject_nonpass_hosted(self):
        self.check_refuse(lambda h: h.update(status='NOT_QUALIFIED'), 'HOSTED_NOT_PASS')

    def test_reject_bogus_hosted_run_id(self):
        self.check_refuse(lambda h: h.update(run_id='0'), 'HOSTED_RUN_ID_INVALID')

    def test_reject_bad_apk_digest(self):
        self.check_refuse(lambda h: h.update(apk_sha256='short'), 'HOSTED_APK_DIGEST_INVALID')

    def test_reject_bad_test_digest(self):
        self.check_refuse(lambda h: h.update(test_apk_sha256='bad'), 'HOSTED_APK_DIGEST_INVALID')

    def test_reject_false_emulator_only(self):
        self.check_refuse(lambda h: h.update(emulator_only=False), 'HOSTED_BOUNDARY_ESCALATION')

    def test_reject_fake_physical(self):
        self.check_refuse(lambda h: h.update(physical_qualified=True), 'HOSTED_BOUNDARY_ESCALATION')

    def test_reject_fake_iceraven(self):
        self.check_refuse(lambda h: h.update(live_iceraven_qualified=True), 'HOSTED_BOUNDARY_ESCALATION')

    def test_reject_nexus_provenance(self):
        self.check_refuse(lambda h: h.update(nexus_file_provenance_verified=True), 'HOSTED_BOUNDARY_ESCALATION')

    def test_reject_prod_game_claim(self):
        self.check_refuse(lambda h: h.update(production_game_unchanged_proven=True), 'HOSTED_BOUNDARY_ESCALATION')

    def test_reject_release_claim(self):
        self.check_refuse(lambda h: h.update(release_qualified=True), 'HOSTED_BOUNDARY_ESCALATION')

    def test_reject_count_drift(self):
        self.check_refuse(lambda h: h.update(tests_passed=3), 'HOSTED_COUNT_MISMATCH')

    def test_reject_missing_case(self):
        self.check_refuse(lambda h: h['cases'].pop(), 'HOSTED_CASE_ROSTER')

    def test_reject_duplicate_case(self):
        self.check_refuse(lambda h: h['cases'].__setitem__(2,h['cases'][0]), 'HOSTED_CASE_ORDER_OR_DUPLICATE')

    def test_reject_nonpass_case(self):
        self.check_refuse(lambda h: h['cases'][1].update(status='NOT_QUALIFIED'), 'HOSTED_CASE_NOT_VERIFIED')

    def test_reject_failure_category(self):
        self.check_refuse(lambda h: h['cases'][0].update(failure_category='ASSERTION'),
                          'HOSTED_CASE_FAILURE_CATEGORY')

    def test_missing_receipt_refuses(self):
        with self.assertRaisesRegex(Refused, 'HOSTED_RECEIPT_NOT_REGULAR'):
            load_hosted(Path('/this_file_does_not_exist_999'))

    def test_unparseable_receipt_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'receipt.json';p.write_text('BAD' * 30)
            with self.assertRaisesRegex(Refused, 'HOSTED_RECEIPT_UNREADABLE'): load_hosted(p)

    def test_symlinked_receipt_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'receipt.json';a.write_text(json.dumps(hosted()))
            b=Path(d)/'alias';b.symlink_to(a)
            with self.assertRaisesRegex(Refused, 'HOSTED_RECEIPT_NOT_REGULAR'):load_hosted(b)

    def test_new_output_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'readiness.json';write_new(p,report(A,B))
            self.assertEqual(json.loads(p.read_text())['schema'],SCHEMA)
            with self.assertRaisesRegex(Refused,'OUTPUT_ALREADY_EXISTS'):write_new(p,report(A,B))

    def test_output_symlink_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'readiness.json';target=Path(d)/'old';target.write_text('private')
            p.symlink_to(target)
            with self.assertRaisesRegex(Refused,'OUTPUT_ALREADY_EXISTS'):write_new(p,report(A,B))
            self.assertEqual(target.read_text(),'private')

    def test_output_has_no_identity_or_credentials(self):
        v=report(A,B,hosted());s=json.dumps(v)
        for secret in ('Authorization','Bearer','token','cookie','/storage/emulated/0','nxm://'):
            self.assertNotIn(secret,s)

    def test_noninteractive_and_no_physical_capabilities(self):
        src=Path(__file__).with_name('cbnx06_lab06_readiness.py').read_text()
        for forbidden in ('import subprocess','import socket','import requests',
                          'adb -s','am instrument','adb install','su -c','deleteRecursively',
                          'gh api','browser.tabs.create'):
            self.assertNotIn(forbidden,src)


if __name__ == '__main__':
    unittest.main(verbosity=2)
