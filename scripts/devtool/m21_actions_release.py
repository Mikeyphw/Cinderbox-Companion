#!/usr/bin/env python3
"""Trusted, source-pinned M21 GitHub release candidate signing & audit.

Runs only from manual GitHub Actions. Never logs, uploads, or emits keystore
bytes, passwords, personal Steam data, or certificate private keys.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


class GateError(Exception):
    pass


def require(condition, code):
    if not condition:
        raise GateError(code)


def run(command, code, *, env=None, binary=False):
    try:
        result = subprocess.run(command, check=False, capture_output=True,
                                timeout=120, env=env, text=not binary)
    except (OSError, subprocess.TimeoutExpired):
        raise GateError(code) from None
    require(result.returncode == 0, code)
    return result.stdout


def android_build_tool(name: str) -> str:
    """Locate the pinned CI SDK build tool; do not depend on runner PATH.

    android-actions/setup-android adds cmdline-tools and platform-tools to PATH,
    but it does not guarantee that build-tools binaries (apksigner/aapt) are
    addressable by bare name. Match the explicitly installed 35.0.0 release SDK.
    """
    require(name in ('apksigner', 'aapt'), 'M21_BUILD_TOOL_NOT_ALLOWLISTED')
    sdk = os.getenv('ANDROID_HOME') or os.getenv('ANDROID_SDK_ROOT')
    if sdk:
        pinned = Path(sdk) / 'build-tools' / '35.0.0' / name
        require(pinned.is_file() and os.access(pinned, os.X_OK),
                'M21_' + name.upper() + '_PINNED_SDK_TOOL_UNAVAILABLE')
        return str(pinned)
    binary = shutil.which(name)
    require(bool(binary), 'M21_' + name.upper() + '_UNAVAILABLE')
    return binary


def pin(value, code):
    require(re.fullmatch(r'[0-9a-fA-F]{64}', value or '') is not None, code)
    return value.lower()


def compare_pins():
    release = pin(os.getenv('CINDERBOX_RELEASE_CERT_SHA256'),
                  'M21_RELEASE_CERT_PIN_REQUIRED')
    debug = pin(os.getenv('CINDERBOX_DEBUG_CERT_SHA256'),
                'M21_DEBUG_CERT_PIN_REQUIRED')
    require(release != debug, 'M21_RELEASE_MUST_NOT_REUSE_DEBUG_CERT')
    return release, debug


def provision(source_dir: Path, runner_temp: Path):
    release_pin, _ = compare_pins()
    encoded = os.getenv('CINDERBOX_RELEASE_KEYSTORE_B64', '')
    password = os.getenv('STORE_PASSWORD', '')
    key_password = os.getenv('KEY_PASSWORD', '')
    require(bool(password and key_password and encoded), 'M21_RELEASE_SECRETS_MISSING')
    require(len(encoded) <= 100000 and re.fullmatch(r'[A-Za-z0-9+/=\s]+', encoded),
            'M21_RELEASE_KEYSTORE_SECRET_INVALID')
    try:
        raw = base64.b64decode(''.join(encoded.split()), validate=True)
    except (binascii.Error, ValueError):
        raise GateError('M21_RELEASE_KEYSTORE_SECRET_INVALID') from None
    require(256 <= len(raw) <= 65536, 'M21_RELEASE_KEYSTORE_SIZE_INVALID')
    signing = runner_temp / 'cinderbox-release-signing'
    signing.mkdir(parents=True, mode=0o700, exist_ok=False)
    key_file = signing / 'keystore.jks'
    with key_file.open('xb') as out:
        out.write(raw)
    key_file.chmod(0o600)
    # Never place the password on a command line or in a log.
    env = dict(os.environ)
    env['STORE_PASSWORD'] = password
    der = run(['keytool', '-exportcert', '-alias', 'cinderbox',
               '-keystore', str(key_file), '-storepass:env', 'STORE_PASSWORD'],
              'M21_RELEASE_KEYSTORE_ALIAS_OR_PASSWORD_INVALID', env=env, binary=True)
    cert = hashlib.sha256(der).hexdigest()
    require(cert == release_pin, 'M21_RELEASE_KEYSTORE_CERTIFICATE_MISMATCH')
    link = source_dir / 'keystore.jks'
    require(not link.exists() and not link.is_symlink(), 'M21_RELEASE_KEYSTORE_PATH_NOT_EMPTY')
    link.symlink_to(key_file)
    require(link.resolve() == key_file.resolve(), 'M21_RELEASE_KEYSTORE_LINK_INVALID')
    print('M21_RELEASE_KEYSTORE_PROVISIONED_AND_PINNED')


def verify(source_dir: Path, stage_dir: Path, source_commit: str, workflow_run: str):
    release_pin, debug_pin = compare_pins()
    require(re.fullmatch(r'[0-9a-f]{40}', source_commit or '') is not None,
            'M21_RELEASE_SOURCE_SHA_INVALID')
    require(re.fullmatch(r'[0-9]{5,20}', workflow_run or '') is not None,
            'M21_RELEASE_WORKFLOW_RUN_INVALID')
    directory = source_dir / 'app/build/outputs/apk/release'
    candidates = list(directory.glob('*.apk'))
    require(len(candidates) == 1, 'M21_RELEASE_APK_COUNT_INVALID')
    apk = candidates[0]
    require(apk.is_file() and not apk.is_symlink() and 0 < apk.stat().st_size <= 200*1024*1024,
            'M21_RELEASE_APK_INVALID')
    output = run([android_build_tool('apksigner'), 'verify', '--verbose', '--print-certs', str(apk)],
                 'M21_RELEASE_APK_SIGNATURE_INVALID')
    match = re.findall(r'(?im)^Signer #\d+ certificate SHA-256 digest:\s*([0-9a-fA-F:]{64,95})\s*$',output)
    require(len(match) == 1, 'M21_RELEASE_APK_SIGNER_AMBIGUOUS')
    actual_cert = match[0].replace(':','').lower()
    require(actual_cert == release_pin and actual_cert != debug_pin,
            'M21_RELEASE_APK_SIGNER_MISMATCH')
    badges = run([android_build_tool('aapt'),'dump','badging',str(apk)],'M21_RELEASE_BADGING_FAILED')
    require(re.search(r"(?m)^package: name='com\.sdvsync' versionCode='[1-9][0-9]*'", badges) is not None,
            'M21_RELEASE_PACKAGE_INVALID')
    require('application-debuggable' not in badges,'M21_RELEASE_APK_DEBUGGABLE')
    version = re.search(r"(?m)^package: name='com\.sdvsync' versionCode='(\d+)' versionName='([^']+)'",badges)
    require(version is not None and len(version.group(2)) <= 64,
            'M21_RELEASE_VERSION_INVALID')
    with apk.open('rb') as stream:
        digest = hashlib.file_digest(stream,'sha256').hexdigest()
    stage_dir.mkdir(parents=True, exist_ok=False)
    target = stage_dir / 'CinderboxCompanion-release-candidate.apk'
    shutil.copyfile(apk,target)
    require(hashlib.sha256(target.read_bytes()).hexdigest() == digest,
            'M21_RELEASE_CANDIDATE_COPY_MISMATCH')
    (stage_dir/'SHA256SUMS').write_text(f'{digest}  {target.name}\n',encoding='utf-8')
    evidence = dict(schema_version=1, producer='cinderbox-m21-manual-release-candidate',
        repository='Mikeyphw/Cinderbox-Companion',source_commit=source_commit,
        workflow_run_id=int(workflow_run), variant='release',package='com.sdvsync',
        version_code=int(version.group(1)),version_name=version.group(2),
        apk_sha256=digest,release_certificate_sha256=actual_cert,
        debug_certificate_sha256=debug_pin,
        signature_verified=True, release_signed=True, debuggable=False,
        installed=False,publication_allowed=False,release_qualified=False,
        device_qualified=False,automatic_publication=False)
    (stage_dir/'M21_RELEASE_CANDIDATE.json').write_text(
        json.dumps(evidence,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('M21_RELEASE_CANDIDATE_VERIFIED')
    print('APK_SHA256='+digest)
    print('RELEASE_CERT_SHA256='+actual_cert)
    print('SOURCE_COMMIT='+source_commit)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command',required=True)
    provision_parser = subs.add_parser('provision')
    provision_parser.add_argument('--source-dir',required=True,type=Path)
    provision_parser.add_argument('--runner-temp',required=True,type=Path)
    verify_parser = subs.add_parser('verify')
    verify_parser.add_argument('--source-dir',required=True,type=Path)
    verify_parser.add_argument('--stage-dir',required=True,type=Path)
    verify_parser.add_argument('--source-commit',required=True)
    verify_parser.add_argument('--workflow-run',required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'provision': provision(args.source_dir,args.runner_temp)
        else: verify(args.source_dir,args.stage_dir,args.source_commit,args.workflow_run)
    except GateError as ex:
        print('FAIL: '+str(ex),file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
