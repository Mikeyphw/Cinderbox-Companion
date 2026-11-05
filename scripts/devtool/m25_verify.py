#!/usr/bin/env python3
"""Independently validate M25 receipt from the same disposable R48 emulator."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
from m25_emulator_ci import TEST_CLASS, TESTS, good, validate_identity


def verify(folder: Path, identity_path: Path, source_sha: str, run_id: str) -> dict:
    assert re.fullmatch(r'[0-9a-f]{40}', source_sha) and re.fullmatch(r'[0-9]+', run_id)
    path = folder / 'M25_PROFILE_EMULATOR_EVIDENCE.json'
    assert path.is_file() and not path.is_symlink() and path.stat().st_size < 24000
    receipt = json.loads(path.read_bytes())
    expected = {
        'schema_version': 1,
        'producer': 'cinderbox-m25-profile-hosted-emulator',
        'overall': 'PASS_M25_PROFILE_HOSTED_EMULATOR',
        'source_sha': source_sha,
        'run_id': run_id,
        'test_class': TEST_CLASS,
        'test_count': len(TESTS),
        'android_api': 36,
        'hosted_emulator_only': True,
        'physical_device_qualified': False,
        'release_qualified': False,
        'publication_allowed': False,
        'automatic_game_update': False,
        'raw_logs_retained': False,
    }
    for name, value in expected.items():
        assert receipt.get(name) == value, 'unexpected M25 evidence field: ' + name
    assert 'raw_output' not in receipt and 'log' not in receipt and 'stacktrace' not in receipt
    report = receipt.get('summary')
    assert isinstance(report, dict) and good(report), 'M25 test receipt is not accepted'
    identity = validate_identity(identity_path, source_sha)
    assert receipt.get('app_apk_sha256') == identity['app_apk_sha256']
    assert receipt.get('android_test_apk_sha256') == identity['android_test_apk_sha256']
    return {
        'overall': 'PASS_M25_EMULATOR_EVIDENCE_VERIFIED',
        'source_sha': source_sha,
        'run_id': run_id,
        'tests_verified': len(TESTS),
        'physical_device_qualified': False,
        'release_qualified': False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--r48-identity', type=Path, required=True)
    p.add_argument('--source-sha', required=True)
    p.add_argument('--run-id', required=True)
    args = p.parse_args()
    try:
        print(json.dumps(verify(args.output_dir, args.r48_identity,
                                args.source_sha, args.run_id), sort_keys=True))
        return 0
    except (AssertionError, ValueError, OSError, TypeError, KeyError, json.JSONDecodeError):
        print('M25_PROFILE_EVIDENCE_REFUSED', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
