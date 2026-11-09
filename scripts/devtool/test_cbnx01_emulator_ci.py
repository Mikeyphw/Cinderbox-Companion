#!/usr/bin/env python3
"""Offline tests for strict hosted CB-NX01 instrumentation evidence."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import cbnx01_instrumentation_receipt as report

ROOT = Path(__file__).resolve().parents[2]
ONE = '''INSTRUMENTATION_STATUS: class=com.sdvsync.mods.api.CbNx01IntentDeviceTest
INSTRUMENTATION_STATUS: current=1
INSTRUMENTATION_STATUS: numtests=1
INSTRUMENTATION_STATUS: test=androidRuntimeRejectsOtherGamesAndExpiredNxm
INSTRUMENTATION_STATUS_CODE: 1
INSTRUMENTATION_STATUS: class=com.sdvsync.mods.api.CbNx01IntentDeviceTest
INSTRUMENTATION_STATUS: current=1
INSTRUMENTATION_STATUS: numtests=1
INSTRUMENTATION_STATUS: test=androidRuntimeRejectsOtherGamesAndExpiredNxm
INSTRUMENTATION_STATUS_CODE: 0
Time: 0.037
OK (1 test)
INSTRUMENTATION_CODE: -1
'''
ZERO = '''Starting 0 tests on emulator-5554 - 16
Tests 0/0 completed. (0 skipped) (0 failed)
Test run failed to complete. Instrumentation run failed due to Process crashed.
'''
H = 'a' * 64
GIT = 'c' * 40


class CbNx01EvidenceTests(unittest.TestCase):
    def test_actual_named_test_passes(self):
        x = report.assess(ONE, '', 0)
        self.assertEqual(x['status'], 'PASS')
        self.assertEqual(x['observed_tests'], 1)
        self.assertFalse(x['failure_codes'])

    def test_gradle_zero_test_crash_is_not_success(self):
        x = report.assess(ZERO, 'E AndroidRuntime: FATAL EXCEPTION: main', 0)
        self.assertEqual(x['status'], 'FAIL')
        self.assertIn('EXACTLY_ONE_TEST_NOT_CONFIRMED', x['failure_codes'])
        self.assertIn('INSTRUMENTATION_PROCESS_CRASHED', x['failure_codes'])

    def test_even_a_zero_exit_and_success_summary_require_named_test(self):
        bad = ONE.replace(report.CLASS, 'com.example.UnrelatedTest')
        self.assertIn('NAMED_TEST_EXECUTION_NOT_CONFIRMED', report.assess(bad, '', 0)['failure_codes'])

    def test_spoofed_one_test_without_success_codes_is_rejected(self):
        bad = ONE.replace('INSTRUMENTATION_CODE: -1', 'INSTRUMENTATION_CODE: 0')
        self.assertIn('INSTRUMENTATION_FINAL_CODE_MISMATCH', report.assess(bad, '', 0)['failure_codes'])

    def test_nonzero_command_is_rejected_despite_success_strings(self):
        self.assertIn('INSTRUMENTATION_COMMAND_FAILED', report.assess(ONE, '', 1)['failure_codes'])

    def test_partial_status_and_multiple_test_sequences_are_rejected(self):
        for value in (ONE.replace('INSTRUMENTATION_STATUS_CODE: 1', ''), ONE + ONE,
                      ONE.replace('numtests=1', 'numtests=2'),
                      ONE.replace(report.METHOD, 'wrongMethod')):
            self.assertEqual(report.assess(value, '', 0)['status'], 'FAIL')

    def test_receipt_exposes_only_sanitized_exception_classes(self):
        sensitive = 'nxm://stardewvalley/mods/123/files/456?key=SECRET_TOKEN_HERE&expires=10000'
        logcat = ('E AndroidRuntime: FATAL EXCEPTION: main\n'
                  'E AndroidRuntime: java.lang.IllegalStateException: ' + sensitive)
        x = report.receipt(ZERO, logcat, 1, source_sha=GIT, run_id='1234',
                           app_sha=H, test_sha=H, installed_sha=H)
        text = json.dumps(x)
        self.assertNotIn('SECRET_TOKEN_HERE', text)
        self.assertNotIn('nxm:', text)
        self.assertIn('java.lang.IllegalStateException', x['exception_types'])
        self.assertFalse(x['release_qualified'])
        self.assertFalse(x['physical_device_qualified'])
        self.assertFalse(x['live_nexus_qualified'])

    def test_installed_app_hash_must_match_built_app(self):
        x = report.receipt(ONE, '', 0, source_sha=GIT, run_id='42',
                           app_sha=H, test_sha=H, installed_sha='b' * 64)
        self.assertIn('INSTALLED_APPLICATION_HASH_MISMATCH', x['failure_codes'])
        self.assertEqual(x['status'], 'FAIL')

    def test_source_and_workflow_require_explicit_runner_with_evidence(self):
        workflow = (ROOT / '.github/workflows/cbnx01-firefox-handoff.yml').read_text()
        runner = (ROOT / 'scripts/devtool/cbnx01_emulator_ci.sh').read_text()
        self.assertNotIn(':app:connectedDebugAndroidTest', workflow)
        self.assertIn('profile: pixel_6', workflow)
        self.assertIn('cores: 2', workflow)
        self.assertIn('ram-size: 2048M', workflow)
        self.assertIn('disk-size: 3072M', workflow)
        self.assertIn('script: bash scripts/devtool/cbnx01_emulator_ci.sh', workflow)
        self.assertIn('if: always()', workflow)
        self.assertIn('cbnx01-api36-policy/STATUS.json', workflow)
        self.assertIn('test_cbnx01_emulator_ci.py', workflow)
        self.assertIn('r48_offline_gate.py --serial "$serial"', runner)
        self.assertIn('am instrument -w -r -e class', runner)
        self.assertIn('com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner', runner)
        self.assertIn('cbnx01_instrumentation_receipt.py', runner)
        self.assertNotIn(':app:connectedDebugAndroidTest', runner)
        self.assertIn("trap 'rm -f", runner)


if __name__ == '__main__':
    unittest.main()
