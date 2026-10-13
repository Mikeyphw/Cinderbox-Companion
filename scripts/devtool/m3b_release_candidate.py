#!/usr/bin/env python3
"""M3B signed *candidate*, never automatic publication. No secrets in evidence.

Requires explicitly enabled policy and an externally provisioned stable key.
CI's default policy is disabled. The Android package manager remains final
upgrade authority; this script cannot prove installed-app compatibility.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

REPO = 'Mikeyphw/Cinderbox-Companion'
PACKAGE = 'com.sdvsync'
POLICY = 'docs/security/M3B_CANDIDATE_POLICY.json'
SHA256 = re.compile(r'[a-f0-9]{64}\Z')
SHA40 = re.compile(r'[a-f0-9]{40}\Z')
CERT = re.compile(r'(?im)^[ \t]*Signer[ \t]*#([0-9]+)[ \t]+certificate[ \t]+SHA-?256[ \t]+digest:[ \t\r\n]*((?:[0-9a-fA-F]{2}:){31}[0-9a-fA-F]{2}|[0-9a-fA-F]{64})')
PKG = re.compile(r"(?m)^package:\s+name='([^']+)'\s+versionCode='(\d+)'\s+versionName='([^']*)'")
MAX_BYTES = 256 * 1024 * 1024


class GateError(ValueError):
    pass


def policy(root: Path, require_enabled: bool = False) -> dict:
    doc = json.loads((root / POLICY).read_text(encoding='utf-8'))
    mandatory = {'schema_version': 1, 'repository': REPO, 'package_name': PACKAGE,
                 'keystore_alias': 'cinderbox', 'publication_enabled': False,
                 'automatic_install': False, 'release_qualified': False,
                 'device_qualification_complete': False}
    for key, value in mandatory.items():
        if doc.get(key) != value:
            raise GateError(f'M3B policy mismatch: {key}')
    if set(doc) != set(mandatory) | {'candidate_signing_enabled', 'certificate_sha256'}:
        raise GateError('Unexpected M3B policy fields')
    enabled = doc.get('candidate_signing_enabled')
    cert = doc.get('certificate_sha256')
    if type(enabled) is not bool:
        raise GateError('candidate_signing_enabled must be a boolean')
    if enabled and (not isinstance(cert, str) or not SHA256.fullmatch(cert)):
        raise GateError('Signed candidates require the pinned 64-hex certificate SHA-256')
    if not enabled and cert is not None:
        raise GateError('Disabled candidate signing must have null fingerprint')
    if require_enabled and not enabled:
        raise GateError('M3B signed candidate disabled; configure stable signing explicitly')
    return doc


def _tool(name: str) -> str:
    path = shutil.which(name)
    if path:
        return path
    sdk = os.getenv('ANDROID_HOME') or os.getenv('ANDROID_SDK_ROOT')
    if sdk:
        candidates = sorted((Path(sdk) / 'build-tools').glob(f'*/{name}'), reverse=True)
        for candidate in candidates:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
    raise GateError(f'Missing Android Build Tools executable: {name}')


def _run(args: list[str]) -> str:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise GateError(f'Cannot run {Path(args[0]).name}') from e
    if p.returncode != 0:
        raise GateError(f'{Path(args[0]).name} returned a failure')
    return p.stdout + '\n' + p.stderr


def sha256(file: Path) -> str:
    h = hashlib.sha256()
    with file.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inspect_apk(apk: Path) -> dict:
    if apk.is_symlink() or not apk.is_file() or not (4096 <= apk.stat().st_size <= MAX_BYTES):
        raise GateError('APK is absent, symlinked, or outside size limits')
    try:
        with zipfile.ZipFile(apk) as z:
            names = z.namelist()
            if len(names) != len(set(names)) or not {'AndroidManifest.xml', 'classes.dex'} <= set(names):
                raise GateError('APK has duplicate entries or missing critical files')
            if z.testzip() is not None:
                raise GateError('APK ZIP integrity failed')
    except zipfile.BadZipFile as exc:
        raise GateError('APK is not a valid ZIP') from exc
    output = _run([_tool('apksigner'), 'verify', '--print-certs', str(apk)])
    signers = [(int(number), digest.replace(':', '').lower()) for number, digest in CERT.findall(output)]
    if not signers or {number for number, _ in signers} != {1} or len({digest for _, digest in signers}) != 1:
        raise GateError('Expected exactly one verifiable APK signing identity')
    try:
        aapt = _run([_tool('aapt'), 'dump', 'badging', str(apk)])
    except GateError:
        aapt = _run([_tool('aapt2'), 'dump', 'badging', str(apk)])
    pkg = PKG.search(aapt)
    if not pkg or pkg.group(1) != PACKAGE or int(pkg.group(2)) < 1:
        raise GateError('APK package identity mismatch')
    return {'package_name': pkg.group(1), 'version_code': int(pkg.group(2)),
            'version_name': pkg.group(3), 'certificate_sha256': signers[0][1],
            'sha256': sha256(apk), 'size_bytes': apk.stat().st_size}


def generate(root: Path, apk: Path, output: Path, expected_sha: str, run_id: str) -> dict:
    p = policy(root, require_enabled=True)
    if not SHA40.fullmatch(expected_sha) or not run_id.isdecimal() or int(run_id) < 1:
        raise GateError('Invalid GitHub run or commit identity')
    head = _run(['git', '-C', str(root), 'rev-parse', 'HEAD']).strip().lower()
    if head != expected_sha or os.getenv('GITHUB_REPOSITORY', REPO) != REPO:
        raise GateError('Source commit/repository does not match current run')
    result = inspect_apk(apk)
    if result['certificate_sha256'] != p['certificate_sha256']:
        raise GateError('Signed candidate certificate is not the pinned stable signing key')
    doc = {'schema_version': 1, 'evidence_kind': 'signed-candidate-self-report',
           'source_commit': expected_sha, 'repository': REPO, 'github_run_id': run_id,
           'artifact': result, 'stable_certificate_match': True,
           'release_qualified': False, 'device_qualified': False,
           'reproducibility_proven': False, 'publication_allowed': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=output.parent, encoding='utf-8', delete=False) as f:
        f.write(json.dumps(doc, sort_keys=True, indent=2) + '\n')
        temp = Path(f.name)
    os.replace(temp, output)
    return doc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['policy', 'require-enabled', 'inspect', 'generate'])
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--apk', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--source-sha', default=os.getenv('GITHUB_SHA', ''))
    parser.add_argument('--run-id', default=os.getenv('GITHUB_RUN_ID', ''))
    args = parser.parse_args()
    try:
        if args.command in ('policy', 'require-enabled'):
            p = policy(args.root, require_enabled=args.command == 'require-enabled')
            print('M3B candidate signing:', 'ENABLED' if p['candidate_signing_enabled'] else 'BLOCKED (default)')
        elif args.command == 'inspect':
            if args.apk is None:
                raise GateError('--apk required')
            print(json.dumps(inspect_apk(args.apk), indent=2, sort_keys=True))
        elif args.command == 'generate':
            if args.apk is None or args.output is None:
                raise GateError('--apk and --output required')
            d = generate(args.root, args.apk, args.output, args.source_sha, args.run_id)
            print('M3B signed candidate verified:', d['artifact']['sha256'])
    except (GateError, OSError, KeyError, json.JSONDecodeError) as e:
        print(f'M3B GATE FAILED: {e}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
