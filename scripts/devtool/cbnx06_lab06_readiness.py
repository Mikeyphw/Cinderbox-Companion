#!/usr/bin/env python3
"""CB-NX06 LAB06 readiness (offline evidence policy, NOT physical qualification).

Never invokes ADB, GH, the browser, a downloader, or mod installation. Produces
one bounded, redacted, source-bound manifest from optional hosted UI evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = 'cbnx06-lab06-deferred-readiness-v1'
HOSTED_SCHEMA = 'cbnx06-lab05-ui-api36-v1'
LAB_PACKAGE = 'com.sdvsync.cbnx06lab'
LAB_GECKO_ID = 'stardew-nexus-download-queue-cbnx06lab@mikeyphw.scriptexts'
LAB_PORT = 38472
CASES = (
    'unpairedConsentRemainsDisabledAfterWindowStart',
    'cancelSyntheticInstallDoesNotWriteModsOrJournal',
    'exactFileCancelKeepsRequestPendingWithoutBrowserLaunch',
    'userConfirmedSyntheticInstallAndRollbackRestoresEmptyLabRoot',
)
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
SAFE_RUN = re.compile(r'[1-9][0-9]{0,23}\Z')

class Refused(ValueError):
    pass


def need(condition: bool, code: str) -> None:
    if not condition:
        raise Refused('LAB06_' + code)


def load_hosted(path: Path) -> dict:
    need(path.is_file() and not path.is_symlink(), 'HOSTED_RECEIPT_NOT_REGULAR')
    need(60 <= path.stat().st_size <= 16_384, 'HOSTED_RECEIPT_SIZE')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise Refused('LAB06_HOSTED_RECEIPT_UNREADABLE') from exc
    need(type(data) is dict, 'HOSTED_RECEIPT_NOT_OBJECT')
    return data


def review_hosted(receipt: dict, source_sha: str) -> tuple[bool, str | None, str | None]:
    """Fail closed on *any* discrepancy; no optimistic partial qualification."""
    need(type(receipt) is dict, 'HOSTED_RECEIPT_INVALID')
    need(receipt.get('schema') == HOSTED_SCHEMA and receipt.get('status') == 'PASS',
         'HOSTED_NOT_PASS')
    need(receipt.get('source_sha') == source_sha, 'HOSTED_SOURCE_MISMATCH')
    need(type(receipt.get('run_id')) is str and SAFE_RUN.fullmatch(receipt['run_id']) is not None,
         'HOSTED_RUN_ID_INVALID')
    for key in ('apk_sha256', 'test_apk_sha256'):
        need(type(receipt.get(key)) is str and HEX64.fullmatch(receipt[key]) is not None,
             'HOSTED_APK_DIGEST_INVALID')
    need(receipt.get('emulator_only') is True and
         receipt.get('physical_qualified') is False and
         receipt.get('live_iceraven_qualified') is False and
         receipt.get('release_qualified') is False and
         receipt.get('nexus_file_provenance_verified') is False and
         receipt.get('production_game_unchanged_proven') is False,
         'HOSTED_BOUNDARY_ESCALATION')
    need(type(receipt.get('actual_test_count')) is int and receipt['actual_test_count'] == 4 and
         type(receipt.get('tests_passed')) is int and receipt['tests_passed'] == 4,
         'HOSTED_COUNT_MISMATCH')
    cases = receipt.get('cases')
    need(type(cases) is list and len(cases) == len(CASES), 'HOSTED_CASE_ROSTER')
    seen = []
    for entry in cases:
        need(type(entry) is dict and entry.get('status') == 'PASS' and
             entry.get('reason') == 'NONE' and entry.get('site') == 'NONE' and
             entry.get('case') in CASES,
             'HOSTED_CASE_NOT_VERIFIED')
        if 'failure_category' in entry:
            need(entry['failure_category'] == 'NONE', 'HOSTED_CASE_FAILURE_CATEGORY')
        seen.append(entry['case'])
    need(tuple(seen) == CASES, 'HOSTED_CASE_ORDER_OR_DUPLICATE')
    return True, receipt['run_id'], receipt['apk_sha256']


def report(source_sha: str, browser_sha: str, hosted: dict | None = None) -> dict:
    need(type(source_sha) is str and HEX40.fullmatch(source_sha) is not None,
         'ANDROID_SOURCE_SHA_INVALID')
    need(type(browser_sha) is str and HEX40.fullmatch(browser_sha) is not None,
         'BROWSER_SOURCE_SHA_INVALID')
    hosted_pass, run, apk = (False, None, None)
    if hosted is not None:
        hosted_pass, run, apk = review_hosted(hosted, source_sha)
    return {
        'schema': SCHEMA,
        'android_pr': 89,
        'browser_pr': 2,
        'android_source_sha': source_sha,
        'browser_source_sha': browser_sha,
        'lab_package': LAB_PACKAGE,
        'gecko_lab_extension_id': LAB_GECKO_ID,
        'lab_loopback_port': LAB_PORT,
        'hosted_ui_api36_pass_source_bound': hosted_pass,
        'hosted_receipt_authenticity_independently_verified': False,
        'github_workflow_conclusion_verified_by_this_tool': False,
        'hosted_ui_run_id': run,
        'hosted_ui_apk_sha256': apk,
        'physical_read_only_acceptance': 'DEFERRED',
        'physical_install_rollback_acceptance': 'DEFERRED',
        'real_iceraven_pairing': 'NOT_WITNESSED',
        'nexus_file_provenance': 'NOT_VERIFIED',
        'physical_qualified': False,
        'live_iceraven_qualified': False,
        'production_game_unchanged_proven': False,
        'release_qualified': False,
        'next_prerequisites': [
            'Successful source-matched LAB05 four-case API36 artifact receipt',
            'Separately verified exact-source LAB APK and isolated LAB XPI bytes',
            'User-authorized read-only physical LAB03B before/after witness',
            'User-performed browser pairing and exact-file action evidence',
            'Separate manual game-isolation and release review',
        ],
        'no_adb_or_device_actions_performed': True,
        'no_production_or_live_nexus_access': True,
    }


def write_new(destination: Path, data: dict) -> None:
    need(destination.parent.is_dir() and not destination.parent.is_symlink(), 'OUTPUT_PARENT_UNSAFE')
    need(not destination.is_symlink() and not destination.exists(), 'OUTPUT_ALREADY_EXISTS')
    payload = (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + '\n').encode()
    need(len(payload) < 8000, 'REPORT_BUDGET')
    # Refuse overwriting any pre-existing evidence, including a competing writer.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW
    fd = os.open(destination, flags, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-sha', required=True)
    ap.add_argument('--browser-sha', required=True)
    ap.add_argument('--hosted-ui-receipt', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    hosted = load_hosted(args.hosted_ui_receipt) if args.hosted_ui_receipt else None
    value = report(args.source_sha, args.browser_sha, hosted)
    write_new(args.output, value)
    print('CBNX06_LAB06_READINESS_REPORT_WRITTEN')
    print('LAB06_HOSTED_API36_SOURCE_BOUND=' + str(value['hosted_ui_api36_pass_source_bound']))
    print('LAB06_PHYSICAL_DEFERRED_NO_DEVICE_OPERATIONS')


if __name__ == '__main__':
    try:
        main()
    except (Refused, OSError) as err:
        print('LAB06_REFUSED ' + str(err), file=sys.stderr)
        raise SystemExit(2)
