#!/usr/bin/env python3
"""Read-only, physical Android 36 CB-NX01 staging witness.

This tool never sends Nexus URLs, keys, cookies, credentials or raw Android logs
into an output file. Machine evidence does NOT establish browser acknowledgement,
file-ID provenance or final integration qualification.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

APP = 'com.sdvsync'
MODS_DIR = '/storage/emulated/0/StardewValley/desktop/Mods'
FIREFOX_PACKAGES = ('org.mozilla.firefox', 'org.mozilla.firefox_beta', 'org.mozilla.fennec_fdroid')
ID = re.compile(r'[1-9][0-9]{0,11}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
SERIAL = re.compile(r'(?:localhost|127\.0\.0\.1):[0-9]{2,5}\Z')
MAX_OUTPUT = 2_000_000


class Refusal(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def git_sha(root: Path) -> str:
    result = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                            capture_output=True, timeout=15, check=False)
    sha = result.stdout.decode('ascii', 'ignore').strip()
    if result.returncode or not HEX40.fullmatch(sha):
        raise Refusal('GIT_SOURCE_ID_UNAVAILABLE')
    return sha


class Adb:
    def __init__(self, serial: str, executable: str = 'adb') -> None:
        if not SERIAL.fullmatch(serial):
            raise Refusal('ADB_SERIAL_MUST_BE_EXPLICIT_LOOPBACK_TCP')
        self.serial, self.executable = serial, executable

    def call(self, *args: str, optional: bool = False) -> bytes | None:
        try:
            proc = subprocess.run([self.executable, '-s', self.serial, *args],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired) as ex:
            raise Refusal('ADB_COMMAND_UNAVAILABLE') from ex
        if len(proc.stdout) > MAX_OUTPUT or len(proc.stderr) > MAX_OUTPUT:
            raise Refusal('ADB_OUTPUT_TOO_LARGE')
        if proc.returncode:
            if optional:
                return None
            # Do not print stderr: provider URLs and user data can appear there.
            raise Refusal('ADB_PROBE_FAILED:' + args[0])
        return proc.stdout

    def text(self, *args: str, optional: bool = False) -> str | None:
        result = self.call(*args, optional=optional)
        return None if result is None else result.decode('utf-8', 'replace').strip()


def apk_info(adb: Adb) -> tuple[str, str]:
    paths = adb.text('shell', 'pm', 'path', APP) or ''
    matches = [p.removeprefix('package:') for p in paths.splitlines()
               if p.startswith('package:') and p.endswith('/base.apk')]
    if len(matches) != 1 or not matches[0].startswith('/data/app/'):
        raise Refusal('CINDERBOX_APP_NOT_INSTALLED_OR_UNEXPECTED_APK_LAYOUT')
    hash_line = adb.text('shell', 'sha256sum', matches[0]) or ''
    match = re.match(r'^([a-f0-9]{64})\s', hash_line)
    if not match:
        raise Refusal('INSTALLED_APK_HASH_UNAVAILABLE')
    return APP, match.group(1)


def private_pending(adb: Adb) -> dict:
    # run-as only works for debug builds, and this is intentionally non-root.
    if adb.text('shell', 'run-as', APP, 'id') is None:
        raise Refusal('DEBUG_RUN_AS_REQUIRED')
    zip_line = adb.text('shell', 'run-as', APP, 'sha256sum',
                        'files/mod-review-pending.zip', optional=True)
    props = adb.text('shell', 'run-as', APP, 'cat',
                     'files/mod-review-pending.properties', optional=True)
    if zip_line is None and props is None:
        return {'present': False}
    if zip_line is None or props is None:
        raise Refusal('PARTIAL_REVIEW_STAGING_FOUND')
    m = re.match(r'^([a-f0-9]{64})\s', zip_line)
    if m is None:
        raise Refusal('REVIEW_ARCHIVE_HASH_UNAVAILABLE')
    size_line = adb.text('shell', 'run-as', APP, 'wc', '-c',
                         'files/mod-review-pending.zip') or ''
    size = re.match(r'^\s*(\d+)\s', size_line)
    if not size or not (1 <= int(size.group(1)) <= 1_073_741_824):
        raise Refusal('REVIEW_ARCHIVE_SIZE_INVALID')
    # Java properties contain the mod name, which is intentionally discarded.
    fields = {}
    for line in props.splitlines():
        key, sep, value = line.partition('=')
        if sep and key in {'source', 'mod_id'}:
            fields[key] = value.strip()
    return {'present': True, 'archive_sha256': m.group(1),
            'archive_bytes': int(size.group(1)),
            'source': fields.get('source', ''), 'mod_id': fields.get('mod_id', '')}


def physical_snapshot(adb: Adb) -> dict:
    if adb.text('get-state') != 'device':
        raise Refusal('ADB_DEVICE_NOT_READY')
    sdk = adb.text('shell', 'getprop', 'ro.build.version.sdk')
    qemu = adb.text('shell', 'getprop', 'ro.kernel.qemu')
    abi = adb.text('shell', 'getprop', 'ro.product.cpu.abi')
    if sdk != '36' or qemu not in ('', '0') or not abi or not abi.startswith('arm64'):
        raise Refusal('PHYSICAL_ARM64_ANDROID36_REQUIRED')
    package, app_sha = apk_info(adb)
    firefox = tuple(p for p in FIREFOX_PACKAGES if adb.text('shell', 'pm', 'path', p, optional=True))
    if not firefox:
        raise Refusal('FIREFOX_ANDROID_NOT_INSTALLED')
    # The output may contain filenames; hash in memory and never persist it.
    listing = adb.call('shell', 'ls', '-laR', MODS_DIR)
    if listing is None or not listing.strip():
        raise Refusal('CINDERBOX_MODS_DIR_UNAVAILABLE')
    return {
        'android_api': 36,
        'device_kind': 'physical-arm64',
        'app_package': package,
        'installed_base_apk_sha256': app_sha,
        'firefox_packages_present': list(firefox),
        'mods_directory_listing_sha256': digest(listing),
        'mods_listing_is_content_digest': False,
        'pending_review': private_pending(adb),
    }


def assess(before: dict, after: dict, expected_mod_id: str, expected_file_id: str) -> dict:
    """Assess machine-visible staging only; never invent a browser acknowledgement."""
    reasons = []
    if before.get('pending_review', {}).get('present'):
        reasons.append('PREEXISTING_PENDING_REVIEW')
    pending = after.get('pending_review', {})
    if not pending.get('present'):
        reasons.append('NO_ARCHIVE_STAGED')
    else:
        if pending.get('source') != 'nexus':
            reasons.append('STAGED_SOURCE_NOT_NEXUS')
        if pending.get('mod_id') != expected_mod_id:
            reasons.append('STAGED_MOD_ID_MISMATCH')
        if not HEX64.fullmatch(str(pending.get('archive_sha256', ''))):
            reasons.append('STAGED_ARCHIVE_HASH_MISSING')
    if before.get('installed_base_apk_sha256') != after.get('installed_base_apk_sha256'):
        reasons.append('INSTALLED_APK_CHANGED')
    if before.get('mods_directory_listing_sha256') != after.get('mods_directory_listing_sha256'):
        reasons.append('MODS_LISTING_CHANGED_BEFORE_APPROVAL')
    if before.get('firefox_packages_present') != after.get('firefox_packages_present'):
        reasons.append('FIREFOX_INSTALLATION_CHANGED')
    # No file-ID metadata, no verified browser callback or independent binary
    # attribution exists in CB-NX01. Be explicit instead of marking it qualified.
    return {
        'status': 'STAGING_OBSERVED_NOT_FULLY_QUALIFIED' if not reasons else 'INCONCLUSIVE',
        'failure_codes': reasons,
        'expected_mod_id': expected_mod_id,
        'expected_file_id': expected_file_id,
        'archive_staging_machine_observed': not reasons,
        'mods_listing_unchanged': 'MODS_LISTING_CHANGED_BEFORE_APPROVAL' not in reasons,
        'mods_file_contents_unchanged_proven': False,
        'exact_file_binary_provenance_verified': False,
        'firefox_to_android_handoff_acknowledged_by_app': False,
        'live_nexus_end_to_end_qualified': False,
        'release_qualified': False,
    }


def write_private(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        json.dump(payload, out, sort_keys=True, indent=2)
        out.write('\n')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['before', 'after'])
    parser.add_argument('--serial', default='localhost:5555')
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--mod-id', help='Selected Nexus mod ID (before only)')
    parser.add_argument('--file-id', help='Selected Nexus file ID (before only)')
    parser.add_argument('--expected-apk-sha256', help='From the independently downloaded CI debug APK (before only)')
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    repo_sha = git_sha(root)
    evidence = args.evidence_dir.expanduser().resolve()
    if evidence == root or root in evidence.parents:
        raise Refusal('EVIDENCE_MUST_BE_OUTSIDE_GIT_REPOSITORY')
    adb = Adb(args.serial)
    if args.phase == 'before':
        if not ID.fullmatch(args.mod_id or '') or not ID.fullmatch(args.file_id or ''):
            raise Refusal('POSITIVE_MOD_AND_FILE_IDS_REQUIRED')
        if (evidence / 'before.json').exists() or (evidence / 'after.json').exists():
            raise Refusal('SESSION_ALREADY_EXISTS')
        snapshot = physical_snapshot(adb)
        if snapshot['pending_review'].get('present'):
            raise Refusal('PREEXISTING_PENDING_REVIEW_CLEAR_MANUALLY_FIRST')
        expected = args.expected_apk_sha256 or ''
        if expected and (not HEX64.fullmatch(expected) or
                         expected != snapshot['installed_base_apk_sha256']):
            raise Refusal('APK_BYTES_DO_NOT_MATCH_EXPECTED_CI_ARTIFACT')
        record = {
            'schema': 'cbnx01-physical-read-only-v1', 'phase': 'before',
            'source_sha': repo_sha, 'observed_at_utc': utcnow(),
            'session_nonce': uuid.uuid4().hex,
            'expected_mod_id': args.mod_id, 'expected_file_id': args.file_id,
            'ci_apk_identity_user_supplied_and_checked': bool(expected),
            'android': snapshot,
            'browser_extension_installed_machine_verified': False,
            'live_nexus_end_to_end_qualified': False,
            'release_qualified': False,
        }
        write_private(evidence / 'before.json', record)
        print('CBNX01_Q01_BEFORE_CAPTURED')
        print('Select Browser + NXM for the chosen file in Cinderbox, then complete any legitimate Nexus and Android prompts. Do not approve/install the archive yet.')
        return 0
    if not (evidence / 'before.json').is_file() or (evidence / 'after.json').exists():
        raise Refusal('BEFORE_RECEIPT_REQUIRED_AND_AFTER_MUST_NOT_EXIST')
    before = json.loads((evidence / 'before.json').read_text(encoding='utf-8'))
    if before.get('schema') != 'cbnx01-physical-read-only-v1' or before.get('phase') != 'before':
        raise Refusal('UNSUPPORTED_BEFORE_RECEIPT')
    if before.get('source_sha') != repo_sha:
        raise Refusal('SOURCE_COMMIT_CHANGED_DURING_ACCEPTANCE')
    snapshot = physical_snapshot(adb)
    evaluation = assess(before['android'], snapshot, before['expected_mod_id'],
                        before['expected_file_id'])
    record = {
        'schema': 'cbnx01-physical-read-only-v1', 'phase': 'after',
        'source_sha': repo_sha, 'observed_at_utc': utcnow(),
        'session_nonce': before['session_nonce'],
        'android': snapshot, 'evaluation': evaluation,
        'browser_extension_installed_machine_verified': False,
        'manual_observation_required': [
            'actual Firefox extension enabled on Android',
            'exact file row and Nexus confirmation observed',
            'Android external-app prompt leads to Cinderbox',
            'review UI shows archive before install',
            'original Mods file bytes remain unchanged'],
    }
    write_private(evidence / 'after.json', record)
    print('CBNX01_Q01_' + evaluation['status'])
    if evaluation['failure_codes']:
        print('CBNX01_Q01_FAILURE_CODES: ' + ','.join(evaluation['failure_codes']))
    print('CBNX01_Q01_NO_FULL_END_TO_END_QUALIFICATION_CLAIM')
    return 0 if not evaluation['failure_codes'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Refusal, ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        detail = str(exc) if isinstance(exc, Refusal) else 'INVALID_INPUT_OR_RECEIPT'
        print('CBNX01_Q01_REFUSED: ' + detail, file=sys.stderr)
        sys.exit(2)
