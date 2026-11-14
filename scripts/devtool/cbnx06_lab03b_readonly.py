#!/usr/bin/env python3
"""LAB03B: read-only, local physical-device/APK/XPI identity and inbox witness.

NO install/launch/root/permission grants/network pairing or game-file access.
Local report files contain only noncredential, bounded proofs. Manual browser
extension acceptance and actual user action are separate from this probe.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
import zipfile

LAB = 'com.sdvsync.cbnx06lab'
PROD = 'com.sdvsync'
GECKO = 'stardew-nexus-download-queue-cbnx06lab@mikeyphw.scriptexts'
PROD_GECKO = 'stardew-nexus-download-queue@mikeyphw.scriptexts'
BROWSERS = ('io.github.forkmaintainers.iceraven', 'org.mozilla.firefox',
            'org.mozilla.firefox_beta', 'org.mozilla.fennec_fdroid')
PREFS = 'shared_prefs/cbnx03b_pairing_inbox.xml'
SERIAL = re.compile(r'(?:localhost|127\.0\.0\.1):[1-9][0-9]{1,4}\Z')
ID = re.compile(r'[1-9][0-9]{0,11}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
SHA40 = re.compile(r'[0-9a-f]{40}\Z')
REQUEST = re.compile(r'[A-Za-z0-9_-]{22,64}\Z')
PACKAGE_PATH = re.compile(r'/data/app/[a-zA-Z0-9._+/~=-]+/base\.apk\Z')
MAX_PRIVATE = 262144
SCHEMA = 'cbnx06-lab03b-readonly-v1'

class Refused(Exception):
    pass

def need(condition, reason):
    if not condition:
        raise Refused(reason)

def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def safe_file(path: Path, low=50, high=1_073_741_824):
    need(path.is_file() and not path.is_symlink() and low <= path.stat().st_size <= high,
         'ARTIFACT_FILE_INVALID')

def validate_artifacts(apk: Path, lab_att: Path, xpi: Path, browser_att: Path,
                       android_sha: str, browser_sha: str) -> dict:
    need(SHA40.fullmatch(android_sha) is not None and SHA40.fullmatch(browser_sha) is not None,
         'SOURCE_SHA_INVALID')
    for path in (lab_att, browser_att): safe_file(path, 80, 200_000)
    safe_file(apk, 100_001, 1_073_741_824)
    safe_file(xpi, 1000, 30_000_000)
    lab = json.loads(lab_att.read_text(encoding='utf-8'))
    browser = json.loads(browser_att.read_text(encoding='utf-8'))
    apk_sha, xpi_sha = sha_file(apk), sha_file(xpi)
    need(lab.get('schema') == 'cbnx06-full-cinderbox-lab-v1' and
         lab.get('source_sha') == android_sha and
         lab.get('application_id') == LAB and
         lab.get('lab_isolated_build') is True and
         lab.get('source_attested') is True and
         lab.get('physical_qualified') is False and
         lab.get('apk_sha256') == apk_sha and
         SHA.fullmatch(str(lab.get('certificate_sha256', ''))) is not None,
         'LAB_APK_ATTESTATION_MISMATCH')
    need(browser.get('schema') == 'cbnx06-lab02c-isolated-unsigned-xpi-v1' and
         browser.get('browser_source_sha') == browser_sha and
         browser.get('extension_id') == GECKO and
         browser.get('production_extension_id') == PROD_GECKO and
         browser.get('android_lab_application_id') == LAB and
         browser.get('android_lab_port') == 38472 and
         browser.get('production_port') == 38471 and
         browser.get('signed') is False and
         browser.get('browser_installed') is False and
         browser.get('physical_qualified') is False and
         browser.get('xpi_sha256') == xpi_sha,
         'BROWSER_XPI_ATTESTATION_MISMATCH')
    with zipfile.ZipFile(xpi) as z:
        items = z.infolist()
        names = [x.filename for x in items]
        need(names and len(names) == len(set(names)) and 'manifest.json' in names and
             'cbnx03-background.js' in names and len(names) <= 150,
             'BROWSER_XPI_ROSTER_INVALID')
        for item in items:
            name = item.filename
            need(not name.startswith('/') and not name.endswith('/') and
                 all(p not in ('.', '..', '') for p in name.split('/')) and
                 item.file_size < 8_000_000 and
                 not stat.S_ISLNK(item.external_attr >> 16), 'BROWSER_XPI_MEMBER_UNSAFE')
        manifest = json.loads(z.read('manifest.json'))
        need(manifest.get('browser_specific_settings', {}).get('gecko', {}).get('id') == GECKO and
             'Cinderbox LAB' in manifest.get('name', ''), 'BROWSER_LAB_ID_MISMATCH')
        need(z.read('cbnx03-background.js').count(b"const BASE = 'http://127.0.0.1:38472'") == 1,
             'BROWSER_LAB_ENDPOINT_MISSING')
        for n in names:
            if n.endswith(('.js', '.html', '.json')):
                need(b'127.0.0.1:38471' not in z.read(n), 'BROWSER_PRODUCTION_PORT_LEAK')
        embedded = browser.get('xpi_file_sha256')
        need(type(embedded) is dict and set(embedded)==set(names),
             'BROWSER_XPI_ATTESTED_ROSTER_MISMATCH')
        for n, hex_hash in embedded.items():
            need(n in names and SHA.fullmatch(str(hex_hash)) is not None and
                 sha_bytes(z.read(n)) == hex_hash, 'BROWSER_XPI_MEMBER_MISMATCH')
    return {'source_sha': android_sha, 'browser_source_sha': browser_sha,
            'apk_sha256': apk_sha, 'lab_signer_cert_sha256': lab['certificate_sha256'],
            'xpi_sha256': xpi_sha, 'gecko_lab_id_verified_in_xpi': True,
            'xpi_signed': False, 'xpi_installed_verified': False}

class Device:
    """Only the following fixed, read-only ADB commands are permitted."""
    def __init__(self, serial='localhost:5555', executable='adb'):
        need(SERIAL.fullmatch(serial) is not None, 'LOOPBACK_DEVICE_SERIAL_REQUIRED')
        self.serial, self.executable = serial, executable

    def run(self, *args, optional=False, max_bytes=MAX_PRIVATE, timeout=30):
        need(args and args[0] in ('get-state', 'shell'), 'ADB_COMMAND_FORBIDDEN')
        try:
            p = subprocess.run([self.executable, '-s', self.serial, *args],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise Refused('ADB_READ_ONLY_TIMEOUT_OR_MISSING') from e
        need(len(p.stdout) <= max_bytes and len(p.stderr) <= 8192, 'ADB_OUTPUT_LIMIT')
        if p.returncode:
            if optional: return None
            raise Refused('ADB_READ_ONLY_FAILED')
        return p.stdout

    def txt(self, *args, optional=False):
        result = self.run(*args, optional=optional)
        return None if result is None else result.decode('utf-8', 'replace').strip()

    def prop(self, key):
        return self.txt('shell', 'getprop', key)

    def package_apk(self, package, required=True):
        need(package in (LAB, PROD) + BROWSERS, 'PACKAGE_NOT_ALLOWLISTED')
        raw = self.txt('shell', 'pm', 'path', package, optional=True)
        if not raw:
            if required: raise Refused('REQUIRED_PACKAGE_MISSING')
            return None
        lines = raw.splitlines()
        base = [x[8:].strip() for x in lines if x.startswith('package:') and x.endswith('/base.apk')]
        need(len(base) == 1 and PACKAGE_PATH.fullmatch(base[0]) is not None,
             'INSTALLED_BASE_APK_INVALID')
        if package == LAB: need(len(lines) == 1, 'LAB_SPLIT_APK_UNEXPECTED')
        return base[0]

    def package_sha(self, path):
        need(PACKAGE_PATH.fullmatch(path) is not None, 'APK_PATH_INVALID')
        value = self.txt('shell', 'sha256sum', path)
        m = re.match(r'([0-9a-f]{64})\s', value or '')
        need(m is not None, 'INSTALLED_APK_HASH_UNAVAILABLE')
        return m.group(1)

    def inbox(self):
        if self.txt('shell', 'run-as', LAB, 'id', optional=True) is None:
            return None  # Neither fake an empty inbox nor fall back to root.
        if self.run('shell', 'run-as', LAB, 'test', '-L', PREFS, optional=True) is not None:
            raise Refused('LAB_INBOX_SYMLINK_REFUSED')
        exists = self.run('shell', 'run-as', LAB, 'test', '-f', PREFS, optional=True)
        if exists is None:
            if self.run('shell', 'run-as', LAB, 'test', '-e', PREFS, optional=True) is not None:
                raise Refused('LAB_INBOX_NOT_REGULAR')
            return []
        data = self.run('shell', 'run-as', LAB, 'cat', PREFS, max_bytes=MAX_PRIVATE)
        return parse_inbox(data)

def parse_inbox(data: bytes) -> list[dict]:
    need(len(data) <= MAX_PRIVATE and b'<!DOCTYPE' not in data and b'<!ENTITY' not in data,
         'LAB_INBOX_XML_UNSAFE')
    try:
        root = ET.fromstring(data)
        need(root.tag == 'map', 'LAB_INBOX_XML_BAD_ROOT')
        rows = [x for x in root if x.attrib.get('name') == 'requests_v1']
        need(len(rows) == 1 and rows[0].tag == 'string', 'LAB_INBOX_ROWS_MISSING')
        parsed = json.loads(rows[0].text or '[]')
        need(type(parsed) is list and len(parsed) <= 40, 'LAB_INBOX_ROWS_INVALID')
        out = []
        used = set()
        for d in parsed:
            need(type(d) is dict and REQUEST.fullmatch(str(d.get('id', ''))) is not None and
                 ID.fullmatch(str(d.get('mod_id', ''))) is not None and
                 ID.fullmatch(str(d.get('file_id', ''))) is not None and
                 d.get('status') in ('PENDING', 'OPENED', 'DISMISSED') and
                 type(d.get('created_at')) is int and d['created_at'] > 0 and
                 d['id'] not in used, 'LAB_INBOX_ROW_UNSAFE')
            used.add(d['id'])
            out.append({k: d[k] for k in ('id', 'mod_id', 'file_id', 'status', 'created_at')})
        return out
    except (ET.ParseError, UnicodeError, ValueError, TypeError, KeyError) as e:
        raise Refused('LAB_INBOX_PARSE_REFUSED') from e

def physical_snapshot(device: Device, expected_apk=None):
    need(device.txt('get-state') == 'device', 'ADB_NOT_READY')
    sdk, abi = device.prop('ro.build.version.sdk'), device.prop('ro.product.cpu.abi')
    hardware = (device.prop('ro.hardware') or '').lower()
    model = (device.prop('ro.product.model') or '').lower()
    fingerprint = (device.prop('ro.build.fingerprint') or '').lower()
    need(sdk == '36' and abi == 'arm64-v8a' and
         device.prop('ro.kernel.qemu') in ('', '0') and
         device.prop('ro.boot.qemu') in ('', '0') and
         not any(x in hardware for x in ('ranchu', 'goldfish', 'cuttlefish', 'vbox', 'qemu')) and
         not any(x in model for x in ('emulator', 'sdk_gphone')) and
         not any(x in fingerprint for x in ('generic_x86', 'sdk_gphone', 'emulator')),
         'PHYSICAL_ANDROID_16_ARM64_REQUIRED')
    browsers = sorted(p for p in BROWSERS if device.package_apk(p, required=False))
    need(bool(browsers), 'FIREFOX_OR_ICERAVEN_BROWSER_REQUIRED')
    prod = device.package_apk(PROD)
    before_hash = device.package_sha(prod)
    lab_path = device.package_apk(LAB, required=False)
    lab_hash = device.package_sha(lab_path) if lab_path else None
    after_hash = device.package_sha(prod)
    need(before_hash == after_hash, 'PRODUCTION_APK_CHANGED_DURING_PROBE')
    if expected_apk is not None:
        need(lab_hash is not None, 'LAB_APP_NOT_INSTALLED_MANUAL_APPROVAL_REQUIRED')
        need(lab_hash == expected_apk, 'LAB_INSTALLED_APK_BYTES_DIFFER_FROM_HOSTED')
    return {'device_api': 36, 'device_abi': abi, 'physical_device': True,
            'browser_packages': browsers, 'production_apk_sha256': before_hash,
            'lab_apk_sha256': lab_hash,
            'lab_apk_exact_bytes_match': expected_apk is not None and lab_hash == expected_apk,
            'production_game_unchanged_proven': False,
            'browser_extension_installed_proven': False,
            'real_nexus_provenance': False, 'release_qualified': False}

def witnessed(rows: list[dict] | None, salt: str, mod_id: str, file_id: str, since_ms=0):
    if rows is None:
        return {'inbox_readable': False, 'request_hashes': [], 'matching_request_hashes': [],
                'recent_matching_request_hashes': []}
    def hashed(row):
        return sha_bytes((salt + ':' + row['id']).encode())
    return {'inbox_readable': True,
            'request_hashes': sorted(hashed(r) for r in rows),
            'matching_request_hashes': sorted(hashed(r) for r in rows
                if r['mod_id'] == mod_id and r['file_id'] == file_id),
            'recent_matching_request_hashes': sorted(hashed(r) for r in rows
                if r['mod_id'] == mod_id and r['file_id'] == file_id and
                type(r.get('created_at')) is int and
                since_ms - 5000 <= r['created_at'] <= int(time.time() * 1000) + 5000)}

def before_snapshot(device: Device, att: dict, mod_id: str, file_id: str):
    need(ID.fullmatch(mod_id) is not None and ID.fullmatch(file_id) is not None,
         'EXACT_MOD_AND_FILE_ID_REQUIRED')
    snap = physical_snapshot(device, att['apk_sha256'])
    salt = uuid.uuid4().hex
    return {'schema': SCHEMA, 'stage': 'before', 'artifacts': att,
            'selected_identity_hash': sha_bytes((salt + ':' + mod_id + ':' + file_id).encode()),
            'salt': salt, 'snapshot': snap,
            'inbox': witnessed(device.inbox(), salt, mod_id, file_id),
            'captured_epoch_ms': int(time.time() * 1000),
            'physical_browser_pairing_proven': False, 'live_nexus_provenance': False,
            'production_game_unchanged_proven': False, 'release_qualified': False}

def assess_after(before: dict, physical: dict, inbox: dict, mod_id: str, file_id: str):
    need(before.get('schema') == SCHEMA and before.get('stage') == 'before', 'BASELINE_SCHEMA_INVALID')
    need(sha_bytes((before['salt'] + ':' + mod_id + ':' + file_id).encode()) ==
         before['selected_identity_hash'], 'SELECTED_IDENTITY_CHANGED')
    first = before['snapshot']
    need(first['physical_device'] and physical['physical_device'] and
         first['production_apk_sha256'] == physical['production_apk_sha256'] and
         first['lab_apk_sha256'] == physical['lab_apk_sha256'] and
         first['browser_packages'] == physical['browser_packages'],
         'PHYSICAL_PACKAGE_IDENTITY_CHANGED')
    old = before['inbox']
    observed = bool(old['inbox_readable'] and inbox['inbox_readable'] and
                    set(inbox['recent_matching_request_hashes']) - set(old['request_hashes']))
    return {'schema': SCHEMA, 'stage': 'after',
            'source_sha': before['artifacts']['source_sha'],
            'browser_source_sha': before['artifacts']['browser_source_sha'],
            'physical_apk_identity_qualified': physical['lab_apk_exact_bytes_match'],
            'production_apk_hash_unchanged': True,
            'new_exact_private_inbox_request_observed': observed,
            'lab_private_inbox_readable': inbox['inbox_readable'],
            'browser_xpi_unsigned': True,
            'browser_extension_installed_proven': False,
            'live_browser_pairing_proven': False,
            'nexus_file_provenance_verified': False,
            'production_game_unchanged_proven': False,
            'rollback_proven': False, 'release_qualified': False,
            'status': 'READ_ONLY_EXACT_INBOX_OBSERVED_NOT_FULLY_QUALIFIED' if observed
                      else 'READ_ONLY_NO_FRESH_INBOX_EVIDENCE_NOT_QUALIFIED'}

def write_new(path: Path, obj: dict):
    need(not path.exists() and not path.is_symlink(), 'LOCAL_RECEIPT_ALREADY_EXISTS')
    need(path.parent.is_dir() and not path.parent.is_symlink(), 'LOCAL_RECEIPT_PARENT_INVALID')
    data = (json.dumps(obj, sort_keys=True, indent=2) + '\n').encode()
    need(len(data) <= 256_000, 'LOCAL_RECEIPT_SIZE_BUDGET')
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as f: f.write(data)

def execute(args):
    dev = Device(args.serial)
    if args.action == 'preflight':
        snap = physical_snapshot(dev)
        print('CBNX06_LAB03B_PHYSICAL_READ_ONLY_PREFLIGHT_PASS')
        print(json.dumps({k:v for k,v in snap.items() if k not in ('production_apk_sha256',)},sort_keys=True,indent=2))
        return
    need(args.mod_id is not None and args.file_id is not None, 'MOD_AND_FILE_REQUIRED')
    session = args.session_dir.expanduser().resolve()
    if args.action == 'before':
        need(not session.exists(), 'SESSION_DIR_ALREADY_EXISTS')
        att = validate_artifacts(args.apk, args.lab_attestation,args.xpi,args.browser_attestation,
                                 args.expected_android_sha,args.expected_browser_sha)
        data = before_snapshot(dev,att,args.mod_id,args.file_id)
        session.mkdir(mode=0o700,parents=True)
        need(not session.is_symlink(), 'SESSION_LINK_REFUSED')
        write_new(session/'before.json',data)
        print('CBNX06_LAB03B_BEFORE_CAPTURED_READ_ONLY_NOT_LIVE_PAIRING_QUALIFIED')
        print('CBNX06_LAB03B_RECEIPT='+str(session/'before.json'))
    else:
        need(session.is_dir() and not session.is_symlink(), 'SESSION_DIR_MISSING')
        baseline = session/'before.json'
        safe_file(baseline, 150, 256_000)
        before = json.loads(baseline.read_text())
        need(before.get('artifacts',{}).get('source_sha') == args.expected_android_sha and
             before.get('artifacts',{}).get('browser_source_sha') == args.expected_browser_sha,
             'SOURCE_MOVED_AFTER_BASELINE')
        snap = physical_snapshot(dev,before['artifacts']['apk_sha256'])
        ins = witnessed(dev.inbox(),before['salt'],args.mod_id,args.file_id,
                        before['captured_epoch_ms'])
        verdict = assess_after(before,snap,ins,args.mod_id,args.file_id)
        path = session/('after-'+str(int(time.time()*1000))+'-'+uuid.uuid4().hex[:8]+'.json')
        write_new(path,verdict)
        print('CBNX06_LAB03B_'+verdict['status'])
        print('CBNX06_LAB03B_RECEIPT='+str(path))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('preflight','before','after'))
    parser.add_argument('--serial', default='localhost:5555')
    parser.add_argument('--apk',type=Path)
    parser.add_argument('--lab-attestation',type=Path)
    parser.add_argument('--xpi',type=Path)
    parser.add_argument('--browser-attestation',type=Path)
    parser.add_argument('--expected-android-sha',default='')
    parser.add_argument('--expected-browser-sha',default='')
    parser.add_argument('--mod-id')
    parser.add_argument('--file-id')
    parser.add_argument('--session-dir',type=Path)
    a=parser.parse_args()
    try:
        if a.action=='before':
            need(all((a.apk,a.lab_attestation,a.xpi,a.browser_attestation,a.session_dir)),
                 'MISSING_HOSTED_ARTIFACTS_OR_SESSION')
        if a.action=='after': need(a.session_dir is not None,'SESSION_REQUIRED')
        execute(a)
    except (Refused, OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print('CBNX06_LAB03B_REFUSED:'+str(exc),file=sys.stderr)
        raise SystemExit(2)
