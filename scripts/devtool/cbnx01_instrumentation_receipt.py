#!/usr/bin/env python3
"""CB-NX01 API36 hosted instrumentation result, fail-closed and sanitized.

The raw instrumentation and Android logcat output stay in temporary files and
are never included in the uploaded receipt, stdout, or Git commit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

CLASS = 'com.sdvsync.mods.api.CbNx01IntentDeviceTest'
METHOD = 'androidRuntimeRejectsOtherGamesAndExpiredNxm'
EXPECTED_SOURCE = 'CBNX01_API36_POLICY'
STATUS_CLASS = re.compile(r'^INSTRUMENTATION_STATUS: class=(.+)$', re.M)
STATUS_METHOD = re.compile(r'^INSTRUMENTATION_STATUS: test=(.+)$', re.M)
STATUS_TESTS = re.compile(r'^INSTRUMENTATION_STATUS: numtests=(\d+)$', re.M)
STATUS_CODE = re.compile(r'^INSTRUMENTATION_STATUS_CODE:\s*(-?\d+)$', re.M)
INSTRUMENTATION_CODE = re.compile(r'^INSTRUMENTATION_CODE:\s*(-?\d+)$', re.M)
TEST_SUMMARY = re.compile(r'^OK \((\d+) test(?:s)?\)$', re.M)
EXCEPTION_CLASS = re.compile(r'\b(?:[a-zA-Z_][\w$]*\.)*[A-Za-z_][\w$]*(?:Exception|Error)\b')
HEX40 = re.compile(r'^[0-9a-f]{40}$')
HEX64 = re.compile(r'^[0-9a-f]{64}$')


def assess(transcript: str, logcat: str, exit_code: int) -> dict:
    """Never accept an empty, partial, mismatched or crashed test transcript."""
    classes = STATUS_CLASS.findall(transcript)
    methods = STATUS_METHOD.findall(transcript)
    declared_counts = STATUS_TESTS.findall(transcript)
    codes = STATUS_CODE.findall(transcript)
    result_codes = INSTRUMENTATION_CODE.findall(transcript)
    summaries = TEST_SUMMARY.findall(transcript)
    observed = int(summaries[-1]) if summaries else 0
    crash = bool(re.search(r'Process crashed|INSTRUMENTATION_FAILED|FATAL EXCEPTION', transcript, re.I))
    crash = crash or 'FATAL EXCEPTION' in logcat
    reasons = []
    if exit_code != 0:
        reasons.append('INSTRUMENTATION_COMMAND_FAILED')
    if crash:
        reasons.append('INSTRUMENTATION_PROCESS_CRASHED')
    if observed != 1 or summaries != ['1']:
        reasons.append('EXACTLY_ONE_TEST_NOT_CONFIRMED')
    if classes != [CLASS, CLASS] or methods != [METHOD, METHOD]:
        # AndroidJUnitRunner emits a start and finish record for each test.
        reasons.append('NAMED_TEST_EXECUTION_NOT_CONFIRMED')
    if not declared_counts or any(c != '1' for c in declared_counts):
        reasons.append('TEST_COUNT_DECLARATION_MISMATCH')
    if codes != ['1', '0']:
        reasons.append('TEST_STATUS_SEQUENCE_MISMATCH')
    if result_codes != ['-1']:
        reasons.append('INSTRUMENTATION_FINAL_CODE_MISMATCH')
    if 'FAILURES!!!' in transcript:
        reasons.append('TEST_FAILURES_REPORTED')
    # Only exception *type names*, never exception messages, URIs or tokens.
    types = sorted(set(EXCEPTION_CLASS.findall(logcat)))[:12]
    return {
        'status': 'PASS' if not reasons else 'FAIL',
        'failure_codes': reasons,
        'expected_test_class': CLASS,
        'expected_test_method': METHOD,
        'expected_tests': 1,
        'observed_tests': observed,
        'emulator_crash_observed': crash,
        'exception_types': types,
    }


def receipt(transcript: str, logcat: str, exit_code: int, *, source_sha: str,
            run_id: str, app_sha: str, test_sha: str, installed_sha: str) -> dict:
    if not HEX40.fullmatch(source_sha):
        raise ValueError('INVALID_SOURCE_SHA')
    for name, val in [('app_sha', app_sha),
                      ('test_sha', test_sha), ('installed_sha', installed_sha)]:
        if not HEX64.fullmatch(val):
            raise ValueError(f'INVALID_{name.upper()}')
    if not re.fullmatch(r'\d{1,20}', run_id):
        raise ValueError('INVALID_GITHUB_RUN_ID')
    result = assess(transcript, logcat, exit_code)
    if app_sha != installed_sha:
        result['failure_codes'].append('INSTALLED_APPLICATION_HASH_MISMATCH')
        result['status'] = 'FAIL'
    return {
        'schema_version': 1,
        'suite': EXPECTED_SOURCE,
        'source_sha': source_sha,
        'github_run_id': run_id,
        'android_api': 36,
        'emulator_arch': 'x86_64',
        'emulator_only': True,
        'physical_device_qualified': False,
        'live_nexus_qualified': False,
        'release_qualified': False,
        'app_apk_sha256': app_sha,
        'test_apk_sha256': test_sha,
        'installed_app_sha256': installed_sha,
        **result,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--instrumentation-log', type=Path, required=True)
    ap.add_argument('--logcat', type=Path, required=True)
    ap.add_argument('--instrument-exit', type=int, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--source-sha', required=True)
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--app-sha', required=True)
    ap.add_argument('--test-sha', required=True)
    ap.add_argument('--installed-sha', required=True)
    args = ap.parse_args()
    result = receipt(
        args.instrumentation_log.read_text(encoding='utf-8', errors='replace'),
        args.logcat.read_text(encoding='utf-8', errors='replace'),
        args.instrument_exit,
        source_sha=args.source_sha, run_id=args.run_id,
        app_sha=args.app_sha, test_sha=args.test_sha, installed_sha=args.installed_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    # Console prints allowlisted status only. Never print raw instrumentation or logcat.
    print('CBNX01_API36_' + result['status'])
    print('CBNX01_API36_FAILURE_CODES: ' + (','.join(result['failure_codes']) or 'none'))
    print('CBNX01_API36_OBSERVED_TESTS: ' + str(result['observed_tests']))
    if result['exception_types']:
        print('CBNX01_API36_EXCEPTION_CLASSES: ' + ','.join(result['exception_types']))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
