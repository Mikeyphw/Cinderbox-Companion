#!/usr/bin/env python3
"""M16: stable, pinned, debug-only CI signing. Never signs releases or changes device data."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import ssl
import subprocess
import sys
import tempfile

REPO = 'Mikeyphw/Cinderbox-Companion'
B64 = 'CINDERBOX_DEBUG_KEYSTORE_B64'
STORE = 'CINDERBOX_DEBUG_STORE_PASSWORD'
KEY = 'CINDERBOX_DEBUG_KEY_PASSWORD'
PIN = 'CINDERBOX_DEBUG_CERT_SHA256'
SHA = re.compile(r'[0-9a-f]{64}\Z')

class GateError(Exception): pass

def need(ok, code):
    if not ok: raise GateError(code)

def fingerprint(path: Path, password: str) -> str:
    env = dict(os.environ, M16_CERT_PASSWORD=password)
    p = subprocess.run(['openssl', 'pkcs12', '-in', str(path), '-clcerts',
                        '-nokeys', '-passin', 'env:M16_CERT_PASSWORD'],
                       env=env, capture_output=True, timeout=30)
    need(p.returncode == 0, 'INVALID_KEYSTORE_OR_PASSWORD')
    certs = re.findall(rb'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', p.stdout, re.S)
    need(len(certs) == 1, 'KEYSTORE_CERTIFICATE_COUNT_INVALID')
    subject = subprocess.run(['openssl', 'x509', '-noout', '-subject', '-nameopt', 'RFC2253'],
                             input=certs[0], capture_output=True, timeout=15)
    need(subject.returncode == 0 and re.search(rb'(?:^|,)CN=Android Debug(?:,|$)',
         subject.stdout.replace(b'subject=', b''), re.I) is not None, 'NOT_A_DEBUG_CERTIFICATE')
    return hashlib.sha256(ssl.PEM_cert_to_DER_cert(certs[0].decode())).hexdigest()

def check_event(env):
    need(env.get('GITHUB_ACTIONS') == 'true' and env.get('GITHUB_REPOSITORY') == REPO,
         'CI_REPOSITORY_NOT_AUTHORIZED')
    event = env.get('GITHUB_EVENT_NAME')
    if event == 'pull_request':
        name = env.get('GITHUB_EVENT_PATH', '')
        need(name and Path(name).is_file(), 'CI_PR_CONTEXT_MISSING')
        pr = json.loads(Path(name).read_text())['pull_request']
        need(pr['head']['repo']['full_name'] == REPO and
             pr['base']['repo']['full_name'] == REPO, 'FORK_PR_SIGNING_DENIED')
    else:
        need(event in ('push', 'workflow_dispatch'), 'CI_EVENT_NOT_AUTHORIZED')

def provision(path: Path, env=None):
    env = os.environ if env is None else env
    check_event(env)
    need(all(env.get(name) for name in (B64, STORE, KEY, PIN)), 'MISSING_DEBUG_SIGNING_CREDENTIALS')
    need(bool(SHA.fullmatch(env[PIN])), 'INVALID_CERTIFICATE_PIN')
    need(len(env[STORE]) >= 16 and len(env[KEY]) >= 16, 'WEAK_DEBUG_PASSWORD')
    need(path.is_absolute() and not path.exists() and not path.is_symlink() and
         path.parent.is_dir() and not path.parent.is_symlink(), 'UNSAFE_KEYSTORE_TARGET')
    try:
        decoded = base64.b64decode(env[B64], validate=True)
    except (ValueError, base64.binascii.Error):
        raise GateError('INVALID_KEYSTORE_BASE64') from None
    need(1024 <= len(decoded) <= 1024*1024, 'INVALID_KEYSTORE_SIZE')
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'wb') as out: out.write(decoded)
        need(fingerprint(path, env[STORE]) == env[PIN], 'KEYSTORE_CERTIFICATE_PIN_MISMATCH')
        github_env = Path(env.get('GITHUB_ENV') or '/nonexistent')
        need(github_env.is_file() and not github_env.is_symlink(), 'GITHUB_ENV_UNAVAILABLE')
        with github_env.open('a') as f:
            f.write('CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING=true\n')
            f.write(f'CINDERBOX_DEBUG_KEYSTORE_PATH={path}\n')
        print('M16 pinned debug keystore provisioned: PASS')
    except Exception:
        path.unlink(missing_ok=True)
        raise

def apk_cert(apk: Path):
    from m3_apk_signing import certificate_sha256, is_android_debug_certificate
    need(apk.is_file() and not apk.is_symlink(), 'APK_NOT_FOUND')
    tool = shutil.which('apksigner')
    if not tool:
        sdk = os.getenv('ANDROID_HOME') or os.getenv('ANDROID_SDK_ROOT')
        if sdk:
            found = sorted((Path(sdk)/'build-tools').glob('*/apksigner'), reverse=True)
            tool = str(found[0]) if found else None
    need(tool is not None, 'APKSIGNER_UNAVAILABLE')
    p = subprocess.run([tool, 'verify', '--print-certs', str(apk)],
                       capture_output=True, timeout=40)
    need(p.returncode == 0, 'APK_SIGNATURE_INVALID')
    need(is_android_debug_certificate(apk), 'APK_CERTIFICATE_NOT_DEBUG')
    return certificate_sha256(apk)

def verify(dirs: list[Path]):
    pin = os.getenv(PIN, '')
    need(bool(SHA.fullmatch(pin)), 'INVALID_CERTIFICATE_PIN')
    for directory in dirs:
        apks = list(directory.glob('*.apk'))
        need(len(apks) == 1, 'EXPECTED_EXACTLY_ONE_APK')
        need(apk_cert(apks[0]) == pin, 'APK_CERTIFICATE_PIN_MISMATCH')
    print('M16 pinned APK signer: PASS (%d APKs)' % len(dirs))

def source_contract(root: Path):
    gradle = (root/'app/build.gradle.kts').read_text()
    need(all(t in gradle for t in ('CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING',
         'CINDERBOX_DEBUG_KEYSTORE_PATH', 'signingConfigs.getByName("ciDebug")')),
         'GRADLE_SIGNING_CONFIG_INCOMPLETE')
    for fn in ('build.yml', 'devtool-android-build.yml'):
        body = (root/'.github/workflows'/fn).read_text()
        for token in ('m16_debug_signing.py provision', 'm16_debug_signing.py verify',
                      'M16 persistent debug signing regressions', B64, STORE, KEY, PIN):
            need(token in body, 'WORKFLOW_SIGNING_INCOMPLETE:' + fn)
        need('assembleRelease' not in body, 'DEBUG_WORKFLOW_MUST_NOT_BUILD_RELEASE')
    print('M16 source contract: PASS')

def setup(directory: Path, upload: bool):
    repo = Path(__file__).resolve().parents[2]
    need(directory.is_absolute() and repo not in directory.parents and directory != repo,
         'KEYSTORE_MUST_BE_OUTSIDE_REPOSITORY')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    need(not directory.is_symlink(), 'KEY_DIRECTORY_SYMLINK_FORBIDDEN')
    os.chmod(directory, 0o700)
    keyfile, pwfile = directory/'cinderbox-debug.p12', directory/'password'
    if not keyfile.exists() and not pwfile.exists():
        need(shutil.which('keytool'), 'KEYTOOL_REQUIRED')
        password = secrets.token_urlsafe(40)
        with tempfile.TemporaryDirectory(dir=directory) as tmp:
            tmpkey = Path(tmp)/'debug.p12'
            command = ['keytool', '-genkeypair', '-noprompt', '-storetype', 'PKCS12',
                       '-alias', 'androiddebugkey', '-keyalg', 'RSA', '-keysize', '3072',
                       '-validity', '10000', '-dname', 'CN=Android Debug,O=Android,C=US',
                       '-keystore', str(tmpkey), '-storepass', password, '-keypass', password]
            result = subprocess.run(command, capture_output=True, timeout=90)
            need(result.returncode == 0 and tmpkey.is_file(), 'KEY_GENERATION_FAILED')
            os.chmod(tmpkey, 0o600)
            tmpkey.replace(keyfile)
            fd = os.open(pwfile, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
            with os.fdopen(fd, 'w') as out: out.write(password)
    need(all(p.is_file() and not p.is_symlink() and p.stat().st_mode & 0o077 == 0
             for p in (keyfile, pwfile)), 'KEYSTORE_OR_PASSWORD_MISSING_OR_UNSAFE')
    password = pwfile.read_text().strip()
    need(len(password) >= 16, 'INVALID_LOCAL_PASSWORD')
    digest = fingerprint(keyfile, password)
    if upload:
        need(shutil.which('gh'), 'GH_REQUIRED')
        # gh reads stdin, keeping private values out of command-line arguments.
        for name, value in ((B64, base64.b64encode(keyfile.read_bytes()).decode()),
                            (STORE, password), (KEY, password)):
            result = subprocess.run(['gh', 'secret', 'set', name, '--repo', REPO],
                                    input=value, text=True, capture_output=True, timeout=60)
            need(result.returncode == 0, 'FAILED_TO_SET_GITHUB_SECRET:' + name)
        result = subprocess.run(['gh', 'variable', 'set', PIN, '--repo', REPO],
                                input=digest, text=True, capture_output=True, timeout=60)
        need(result.returncode == 0, 'FAILED_TO_SET_GITHUB_CERT_PIN')
        print('M16 GitHub repository secrets and public pin: configured')
    print('M16 stable debug certificate SHA256=' + digest)
    print('Local key: ' + str(keyfile))
    print('Back up this keystore AND password securely; never commit either.')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    s = sub.add_parser('setup')
    s.add_argument('--upload', action='store_true')
    s.add_argument('--directory', type=Path,
                   default=Path.home()/'.local/share/cinderbox/debug-signing')
    c = sub.add_parser('provision')
    c.add_argument('--path', required=True, type=Path)
    v = sub.add_parser('verify')
    v.add_argument('--apk-dir', required=True, action='append', type=Path)
    t = sub.add_parser('source')
    t.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    a = p.parse_args()
    try:
        if a.action == 'setup': setup(a.directory.expanduser().resolve(), a.upload)
        elif a.action == 'provision': provision(a.path)
        elif a.action == 'verify': verify(a.apk_dir)
        else: source_contract(a.repo)
    except (GateError, OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        # Never print exception arguments: they may contain sensitive paths or bytes.
        kind = sys.exc_info()[1]
        print('M16 FAIL: ' + (str(kind) if isinstance(kind, GateError)
                              else 'UNEXPECTED_SIGNING_FAILURE'), file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__': sys.exit(main())
