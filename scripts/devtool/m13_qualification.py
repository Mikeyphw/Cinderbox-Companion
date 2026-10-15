#!/usr/bin/env python3
"""M13 fail-closed debug qualification. No signing, installs, publication or personal data.

Commands:
  source    Verify producer->consumer contracts, CI lanes and release policy.
  finalize  Verify a just-built M3 debug APK evidence file against local APK bytes.
  ci        Verify GitHub REST run/jobs JSON supplied as explicit trusted observations.
  device    Read-only, opt-in ADB environment observation (not functional testing).

M13 does not establish release qualification; it records only the evidence actually observed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

REPO = 'Mikeyphw/Cinderbox-Companion'
COMMIT = re.compile(r'[0-9a-f]{40}\Z')
DIGEST = re.compile(r'[0-9a-f]{64}\Z')
WORKFLOWS = ('.github/workflows/build.yml', '.github/workflows/devtool-android-build.yml')
LEGACY_SUITES = ('m3', 'm3g', 'm4', 'm5', 'm6', 'm7', 'm7b', 'm8', 'm9', 'm10', 'm11', 'm12', 'm13')
RECOVERY_CONTRACTS = (
    ('game_download', 'm6-game-download.properties',
     'app/src/main/java/com/sdvsync/download/GameDownloadRecovery.kt',
     'app/src/main/java/com/sdvsync/ui/viewmodels/GameDownloadViewModel.kt', 'canResume('),
    ('mod_profile', 'm8-profile-transaction.properties',
     'app/src/main/java/com/sdvsync/mods/ModProfileTransaction.kt',
     'app/src/main/java/com/sdvsync/mods/ModFileManager.kt', 'profileTransactions.recover()'),
    ('mod_batch', 'm9-mod-batch.properties',
     'app/src/main/java/com/sdvsync/mods/ModBatchTransaction.kt',
     'app/src/main/java/com/sdvsync/mods/ModFileManager.kt', 'batchTransactions.recover()'),
    ('game_repair', 'm10-game-repair.properties',
     'app/src/main/java/com/sdvsync/download/VerifiedGameRepair.kt',
     'app/src/main/java/com/sdvsync/ui/screens/InstallationHealthScreen.kt', 'recover()'),
    ('save_restore', 'm11-save-restore.properties',
     'app/src/main/java/com/sdvsync/saves/SaveRestoreTransaction.kt',
     'app/src/main/java/com/sdvsync/saves/SaveBackupManager.kt', 'SaveRestoreTransaction'),
)

class GateError(Exception):
    pass


def insist(condition: bool, description: str):
    if not condition:
        raise GateError(description)


def load_json(path: Path) -> dict:
    insist(path.is_file() and not path.is_symlink() and path.stat().st_size <= 2_000_000,
           'Unsafe or oversized evidence file')
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError) as exc:
        raise GateError('Invalid evidence JSON') from exc
    insist(type(value) is dict, 'Evidence is not an object')
    return value


def read_source(root: Path, relative: str) -> str:
    file = root / relative
    insist(file.is_file() and not file.is_symlink(), 'Missing required tracked source: ' + relative)
    return file.read_text(encoding='utf-8')


def sha256(file: Path) -> str:
    h = hashlib.sha256()
    with file.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def source_audit(root: Path) -> dict:
    policy = load_json(root / 'docs/security/M3_RELEASE_POLICY.json')
    required = {'schema_version': 1, 'repository': REPO, 'package_name': 'com.sdvsync',
                'ci_build_variant': 'debug', 'ci_artifact_format': 'apk', 'release_enabled': False,
                'publication_enabled': False, 'automatic_device_install': False,
                'device_qualification_complete': False, 'release_signing_certificate_sha256': None,
                'release_keystore_source': None}
    insist(all(type(policy.get(k)) is type(v) and policy.get(k) == v for k, v in required.items()),
           'Production release policy changed: explicit security review required')
    candidate = load_json(root / 'docs/security/M3B_CANDIDATE_POLICY.json')
    insist(type(candidate.get('candidate_signing_enabled')) is bool and
           candidate.get('publication_enabled') is False and
           candidate.get('automatic_install') is False and
           candidate.get('release_qualified') is False and
           candidate.get('device_qualification_complete') is False,
           'Signed-candidate policy permits publishing/installing or overclaims qualification')
    if candidate['candidate_signing_enabled']:
        insist(type(candidate.get('certificate_sha256')) is str and
               DIGEST.fullmatch(candidate['certificate_sha256']) is not None,
               'Enabled candidate signing has no pinned certificate')
    else:
        insist(candidate.get('certificate_sha256') is None,
               'Disabled candidate signing has stale certificate configuration')
    evidence = read_source(root, 'app/src/main/java/com/sdvsync/diagnostics/OperationCenterEvidence.kt')
    manager = read_source(root, 'app/src/main/java/com/sdvsync/mods/ModFileManager.kt')
    assessed = []
    for key, journal, producer, consumer, call in RECOVERY_CONTRACTS:
        p = read_source(root, producer)
        c = read_source(root, consumer)
        insist(journal in p and journal in evidence, 'Missing producer/observer journal: ' + key)
        insist(call in c, 'Recovery consumer not connected: ' + key)
        insist(('fun recover()' in p or 'fun pending()' in p), 'Recovery API missing: ' + key)
        assessed.append({'id': key, 'status': 'PASS'})
    insist('batchTransactions.recover()' in manager and 'profileTransactions.recover()' in manager,
           'Mod manager is missing pre-mutation recovery')
    insist('mod-review-pending' in evidence, 'Mod review marker missing from operation center')
    insist('LinkOption.NOFOLLOW_LINKS' in evidence, 'Marker observer follows symlinks')
    screen = read_source(root, 'app/src/main/java/com/sdvsync/ui/screens/OperationCenterScreen.kt')
    for disallowed in ('.startDownload(', '.cancelDownload()', '.recover()', '.deleteRecursively('):
        insist(disallowed not in screen, 'Operation center became a mutating action surface')
    checks = read_source(root, 'scripts/devtool/m3_build_evidence.py')
    insist('qualified_release": False' in checks and 'publication_allowed": False' in checks,
           'M3 debug evidence release restrictions were removed')
    for wf in WORKFLOWS:
        body = read_source(root, wf)
        for suite in LEGACY_SUITES:
            insist('test_' + suite + '_*.py' in body, 'Missing milestone test lane: ' + suite)
        insist('m13_qualification.py source' in body and
               'm13_qualification.py finalize' in body, 'Missing M13 release gate from workflow')
        insist('m3_build_evidence.py generate' in body, 'Missing provenance producer')
        insist('assembleDebug' in body and 'assembleRelease' not in body,
               'Debug workflow has unexpected APK build variant')
        insist('M13_QUALIFICATION.json' in body, 'Qualification evidence not included in artifact')
    return {'release_policy': 'BLOCKED_BY_POLICY', 'debug_source_contract': 'PASS',
            'cross_feature_checks': assessed,
            'instrumentation': 'NOT_RUN', 'real_device': 'NOT_RUN'}


def current_commit(root: Path) -> str:
    p = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                       capture_output=True, text=True, check=False, timeout=8)
    sha = p.stdout.strip()
    insist(p.returncode == 0 and COMMIT.fullmatch(sha) is not None, 'Git source commit unavailable')
    return sha


def base_report(source: str) -> dict:
    return {'schema_version': 1, 'producer': 'cinderbox-m13', 'repository': REPO,
            'source_commit': source, 'qualification_scope': 'debug-automation-only',
            'source_contract': 'NOT_RUN', 'debug_build': 'NOT_RUN',
            'apk_integrity': 'NOT_RUN', 'ci_run': 'NOT_RUN',
            'automated_device_probe': 'NOT_RUN', 'instrumentation': 'NOT_RUN',
            'release_signing': 'BLOCKED_BY_POLICY', 'release_qualified': False,
            'publication_allowed': False, 'device_qualified': False,
            'automatic_device_install': False}


def atomic_json(path: Path, document: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    insist(not path.is_symlink(), 'Output symlink blocked')
    fd, name = tempfile.mkstemp(prefix='.m13-', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(document, stream, sort_keys=True, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def finalize(root: Path, provenance: Path, apk: Path, expected: str) -> dict:
    insist(COMMIT.fullmatch(expected) is not None and current_commit(root) == expected,
           'Source commit mismatch')
    matrix = source_audit(root)
    m3 = load_json(provenance)
    insist(m3.get('schema_version') == 1 and
           m3.get('evidence_kind') == 'ci-build-self-report' and
           m3.get('source_commit') == expected and m3.get('repository') == REPO and
           m3.get('variant') == 'debug' and m3.get('format') == 'apk',
           'M3 source/provenance mismatch')
    for claim in ('qualified_release', 'publication_allowed', 'reproducibility_proven', 'device_qualified'):
        insist(m3.get(claim) is False, 'M3 made unsupported qualification claim')
    info = m3.get('apk')
    insist(type(info) is dict and DIGEST.fullmatch(info.get('sha256', '')) is not None,
           'Missing M3 APK digest')
    insist(apk.is_file() and not apk.is_symlink() and
           apk.name == info.get('filename') and apk.stat().st_size == info.get('size_bytes') and
           sha256(apk) == info['sha256'], 'APK bytes do not match M3 evidence')
    insist(info.get('signature_verified') is True and info.get('debug_signed') is True and
           info.get('package_name') == 'com.sdvsync', 'M3 debug package metadata unverified')
    doc = base_report(expected)
    doc.update(source_contract='PASS', debug_build='PASS_OBSERVED_IN_CI_STEP',
               apk_integrity='PASS_SHA256_MATCHES_M3', cross_feature=matrix['cross_feature_checks'],
               artifact_sha256=info['sha256'], build_provenance='CI_SELF_REPORT_NOT_ATTESTATION')
    return doc


# GitHub REST run + jobs are supplied explicitly; this tool never claims network provenance.
REQUIRED_CI_STEPS = (
    'Validate debug-only source and signing policy',
    'Run M3 source regression tests',
    'M3G Steam regression tests',
    'M4 local-first safety regressions',
    'M5 safe operations regressions',
    'M6 interrupted download recovery regressions',
    'M7 mod compatibility regressions',
    'M7B preview and sanitized report regressions',
    'M8 crash-safe mod profile regressions',
    'M9 atomic multi-mod transaction regressions',
    'M10 selective verified game repair regressions',
    'M11 capacity and save recovery regressions',
    'M12 operation center and safe export regressions',
    'M13 integration and release-gate regressions',
    'Enforce M3B non-publishing policy and regressions',
    'Offline M0/M1 security source contract',
    'Test, lint, and build debug APK',
    'Generate verified APK metadata and source evidence',
    'Generate M13 debug qualification evidence',
    'Upload debug APK',
)


def assess_ci(run: dict, jobs: dict, expected_sha: str, local_evidence: dict | None = None) -> dict:
    insist(COMMIT.fullmatch(expected_sha) is not None, 'Expected trusted commit must be a full SHA')
    insist(run.get('head_sha') == expected_sha and
           run.get('repository', {}).get('full_name') == REPO,
           'GitHub run does not match expected source or repo')
    insist(run.get('status') == 'completed' and run.get('conclusion') == 'success',
           'GitHub workflow did not complete successfully')
    insist(run.get('name') == 'Build Debug APK' and
           run.get('event') in ('push', 'pull_request'), 'Unrecognized CI workflow or trigger')
    insist(isinstance(run.get('id'), int) and run['id'] > 0,
           'Invalid CI run ID')
    work = jobs.get('jobs')
    insist(type(work) is list and len(work) == 1 and
           work[0].get('name') == 'build' and work[0].get('conclusion') == 'success',
           'CI build job missing or incomplete')
    steps = work[0].get('steps')
    insist(type(steps) is list, 'CI steps missing')
    names = [x.get('name') for x in steps]
    insist(len(names) == len(set(names)), 'Duplicate CI step names')
    for name in REQUIRED_CI_STEPS:
        insist(name in names and steps[names.index(name)].get('conclusion') == 'success',
               'Required CI step skipped or failed: ' + name)
    doc = base_report(expected_sha)
    doc.update(ci_run='PASS_GITHUB_REST_OBSERVATION', github_run_id=run['id'],
               debug_build='PASS_GITHUB_REST_OBSERVATION')
    if local_evidence is not None:
        insist(local_evidence.get('producer') == 'cinderbox-m13' and
               local_evidence.get('source_commit') == expected_sha and
               local_evidence.get('source_contract') == 'PASS' and
               local_evidence.get('apk_integrity') == 'PASS_SHA256_MATCHES_M3' and
               local_evidence.get('release_qualified') is False,
               'Local artifact report is missing or mismatched')
        doc.update(source_contract='PASS', apk_integrity='PASS_SHA256_MATCHES_M3',
                   artifact_sha256=local_evidence['artifact_sha256'])
    return doc


def device_probe(root: Path) -> dict:
    insist(current_commit(root) is not None, 'No local source commit')
    def adb(*params: str) -> str:
        try:
            p = subprocess.run(['adb', *params], capture_output=True, text=True,
                               timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GateError('ADB unavailable; observation NOT_RUN') from exc
        insist(p.returncode == 0, 'ADB observation failed; no device qualification')
        return p.stdout.strip()
    raw = adb('devices')
    devices = [parts[0] for line in raw.splitlines()[1:] if
               (parts := line.split()) and len(parts) == 2 and parts[1] == 'device']
    insist(len(devices) == 1, 'Exactly one authorized ADB device required')
    serial = devices[0]  # never persisted, returned, or logged
    sdk = adb('-s', serial, 'shell', 'getprop', 'ro.build.version.sdk')
    abi = adb('-s', serial, 'shell', 'getprop', 'ro.product.cpu.abi')
    insist(sdk.isdecimal() and 20 <= int(sdk) <= 100 and
           abi in ('arm64-v8a', 'armeabi-v7a', 'x86', 'x86_64'),
           'Unsupported device properties')
    # pm path reads package-manager state; it neither installs nor launches the application.
    pkg = adb('-s', serial, 'shell', 'pm', 'path', 'com.sdvsync')
    doc = base_report(current_commit(root))
    doc.update(automated_device_probe='PASS_READ_ONLY_PROPERTIES', android_api=int(sdk),
               device_abi=abi, app_package_observed=any(line.startswith('package:') for line in pkg.splitlines()))
    return doc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('source', 'finalize', 'ci', 'device'))
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--provenance', type=Path)
    parser.add_argument('--apk', type=Path)
    parser.add_argument('--source-sha', default=os.getenv('GITHUB_SHA', ''))
    parser.add_argument('--run-json', type=Path)
    parser.add_argument('--jobs-json', type=Path)
    parser.add_argument('--artifact-report', type=Path)
    a = parser.parse_args(argv)
    try:
        if a.action == 'source':
            doc = source_audit(a.root)
            print('M13 source and release boundary: PASS (production release BLOCKED)')
        elif a.action == 'finalize':
            insist(a.provenance is not None and a.apk is not None and a.output is not None,
                   'finalize requires provenance, apk and output')
            doc = finalize(a.root, a.provenance, a.apk, a.source_sha)
            atomic_json(a.output, doc)
            print('M13 debug evidence: PASS (production release BLOCKED)')
        elif a.action == 'ci':
            insist(a.run_json is not None and a.jobs_json is not None and a.output is not None,
                   'ci requires run JSON, jobs JSON and output')
            evidence = load_json(a.artifact_report) if a.artifact_report else None
            doc = assess_ci(load_json(a.run_json), load_json(a.jobs_json), a.source_sha, evidence)
            atomic_json(a.output, doc)
            print('M13 CI observation: PASS (production release BLOCKED)')
        else:
            insist(a.output is not None, 'device requires output')
            doc = device_probe(a.root)
            atomic_json(a.output, doc)
            print('M13 read-only device probe: PASS (device functional testing NOT_RUN)')
        return 0
    except (GateError, OSError, ValueError) as exc:
        print('M13 QUALIFICATION BLOCKED:', exc, file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
