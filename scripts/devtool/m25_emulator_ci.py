#!/usr/bin/env python3
"""Run four metadata-only M25 tests on the existing R48 API36 Linux/KVM AVD.

No device other than emulator-5554, no signing secrets, root, Steam, GameFiles,
private data or raw instrumentation output. The R48 installer has already
verified both APK SHA256 values, the signer and the installed app bytes.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

APP_PACKAGE = 'com.sdvsync'
TEST_PACKAGE = 'com.sdvsync.test'
TEST_RUNNER = 'androidx.test.runner.AndroidJUnitRunner'
TEST_CLASS = 'com.sdvsync.mods.profile.M25PortableProfileDeviceTest'
TESTS = (
    'metadataRoundtripAndNoPaths',
    'legacyMigrationIsStableAcrossLoadsAndStoreWrites',
    'rejectsDuplicateIdsAndUnexpectedSchema',
    'rejectsInvalidUtf8OversizeAndCorruptLegacyWithoutMutatingBytes',
)


def summary(stdout: str, returncode: int) -> dict:
    started, passed, failed, unknown = set(), set(), set(), set()
    active = None
    sequences = {name: [] for name in TESTS}
    terminal_codes = []
    for line in stdout.splitlines():
        if line.startswith('INSTRUMENTATION_STATUS: test='):
            name = line.partition('=')[2].strip()
            active = name if name in TESTS else None
            if active is None:
                unknown.add('unknown_test')
        elif line.startswith('INSTRUMENTATION_STATUS_CODE: '):
            code = line.partition(': ')[2].strip()
            if active is not None:
                if code == '1':
                    started.add(active)
                    sequences[active].append('start')
                elif code == '0':
                    passed.add(active)
                    sequences[active].append('pass')
                elif code in ('-1', '-2'):
                    failed.add(active)
                    sequences[active].append('fail')
                else:
                    unknown.add('unknown_status')
            active = None
        elif line.startswith('INSTRUMENTATION_CODE: '):
            terminal_codes.append(line.partition(': ')[2].strip())
    passed -= failed
    diagnostics = {
        'assertion': ('AssertionError', 'AssertionFailedError', 'ComparisonFailure'),
        'instrumentation_crash': ('Process crashed', 'INSTRUMENTATION_FAILED', 'shortMsg='),
        'instrumentation_abort': ('INSTRUMENTATION_ABORTED',),
    }
    result = {
        'expected_tests': list(TESTS),
        'started_tests': [name for name in TESTS if name in started],
        'passed_tests': [name for name in TESTS if name in passed],
        'failed_tests': [name for name in TESTS if name in failed],
        'unknown_test_present': bool(unknown),
        'exact_event_sequence': all(events == ['start', 'pass']
                                    for events in sequences.values()),
        'terminal_success': terminal_codes == ['-1'],
        'reported_ok': bool(re.search(r'(?m)^OK \(4 tests\)\s*$', stdout)),
        'error_categories': [k for k, needles in diagnostics.items()
                             if any(v in stdout for v in needles)],
        'raw_logs_retained': False,
        'exit_zero': returncode == 0,
    }
    return result


def good(result: dict) -> bool:
    return (
        result['started_tests'] == list(TESTS)
        and result['passed_tests'] == list(TESTS)
        and result['failed_tests'] == []
        and not result['unknown_test_present']
        and result.get('exact_event_sequence') is True
        and result['terminal_success'] and result['reported_ok']
        and result['exit_zero'] and result['error_categories'] == []
    )


def command(*args: str, timeout: int = 30) -> str:
    value = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if value.returncode != 0:
        raise RuntimeError('command refused')
    return value.stdout.strip()


def inspect_emulator(serial: str) -> None:
    if serial != 'emulator-5554':
        raise RuntimeError('unexpected emulator serial')
    online = command('adb', 'devices').splitlines()[1:]
    connected = [v.split()[0] for v in online if len(v.split()) == 2 and v.split()[1] == 'device']
    if connected != [serial]:
        raise RuntimeError('other or missing Android transport')
    def adb(*args: str) -> str:
        return command('adb', '-s', serial, *args)
    if adb('shell', 'getprop', 'ro.kernel.qemu').strip() != '1':
        raise RuntimeError('physical device refused')
    if adb('shell', 'getprop', 'ro.build.version.sdk').strip() != '36':
        raise RuntimeError('API36 required')
    if 'Override size: 640x1440' not in adb('shell', 'wm', 'size'):
        raise RuntimeError('R48 compact viewport not active')
    if 'Override density: 320' not in adb('shell', 'wm', 'density'):
        raise RuntimeError('R48 compact density not active')
    if adb('shell', 'settings', 'get', 'system', 'font_scale') != '1.6':
        raise RuntimeError('R48 font scaling not active')
    if 'package:/data/app/' not in adb('shell', 'pm', 'path', APP_PACKAGE):
        raise RuntimeError('R48 application not installed')
    if 'package:/data/app/' not in adb('shell', 'pm', 'path', TEST_PACKAGE):
        raise RuntimeError('R48 test APK not installed')
    if TEST_PACKAGE + '/' + TEST_RUNNER not in adb('shell', 'pm', 'list', 'instrumentation'):
        raise RuntimeError('incorrect Android test runner')


def validate_identity(path: Path, source_sha: str) -> dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 10000:
        raise RuntimeError('missing R48 APK identity')
    identity = json.loads(path.read_bytes())
    if identity.get('schema_version') != 1 or identity.get('source_sha') != source_sha:
        raise RuntimeError('APK source mismatch')
    if identity.get('package') != APP_PACKAGE or identity.get('app_is_debug') is not True:
        raise RuntimeError('wrong APK identity')
    if identity.get('physical_device_qualified') is not False or identity.get('release_qualified') is not False:
        raise RuntimeError('release or device claim forbidden')
    for key in ('app_apk_sha256', 'android_test_apk_sha256', 'installed_base_apk_sha256',
                'debug_signing_certificate_sha256'):
        if not re.fullmatch(r'[0-9a-f]{64}', identity.get(key, '')):
            raise RuntimeError('invalid APK digest')
    if identity['app_apk_sha256'] != identity['installed_base_apk_sha256']:
        raise RuntimeError('installed app does not match the APK')
    return identity


def run(output: Path, identity_path: Path) -> bool:
    output.mkdir(parents=True, exist_ok=True)
    source_sha = os.environ.get('GITHUB_SHA', '')
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    evidence = {
        'schema_version': 1,
        'producer': 'cinderbox-m25-profile-hosted-emulator',
        'overall': 'REFUSED',
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
    path = output / 'M25_PROFILE_EMULATOR_EVIDENCE.json'
    try:
        if not re.fullmatch(r'[0-9a-f]{40}', source_sha) or not re.fullmatch(r'[0-9]+', run_id):
            raise RuntimeError('invalid GitHub source identity')
        if os.environ.get('RUNNER_OS') != 'Linux' or command('uname', '-m') != 'x86_64':
            raise RuntimeError('unsupported CI host')
        if command('git', 'rev-parse', 'HEAD') != source_sha:
            raise RuntimeError('checkout/source mismatch')
        if not os.environ.get('RUNNER_TEMP'):
            raise RuntimeError('missing ephemeral runner temp')
        identity = validate_identity(identity_path, source_sha)
        inspect_emulator('emulator-5554')
        installed_path = command('adb', '-s', 'emulator-5554', 'shell', 'pm', 'path', APP_PACKAGE)
        found = re.search(r'(?m)^package:(/data/app/[^\r\n]+/base\.apk)\s*$', installed_path)
        if not found:
            raise RuntimeError('unexpected installed APK location')
        installed_sha = command('adb', '-s', 'emulator-5554', 'shell', 'sha256sum', found.group(1)).split()[0]
        if installed_sha != identity['app_apk_sha256']:
            raise RuntimeError('R48 installed APK identity drift')
        # Never print raw instrument output: it may include arbitrary paths, test data or stack traces.
        cmd = ['adb', '-s', 'emulator-5554', 'shell', 'am', 'instrument', '-w', '-r',
               '-e', 'class', TEST_CLASS, TEST_PACKAGE + '/' + TEST_RUNNER]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        report = summary(result.stdout, result.returncode)
        evidence['summary'] = report
        evidence['app_apk_sha256'] = identity['app_apk_sha256']
        evidence['android_test_apk_sha256'] = identity['android_test_apk_sha256']
        if not good(report):
            raise RuntimeError('profile instrumentation not accepted')
        evidence['overall'] = 'PASS_M25_PROFILE_HOSTED_EMULATOR'
        print('M25_EMULATOR_PROFILE_4_TESTS_PASS')
        return True
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError, KeyError, TypeError):
        print('M25_EMULATOR_REFUSED', file=sys.stderr)
        return False
    finally:
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--r48-identity', type=Path, required=True)
    args = parser.parse_args()
    return 0 if run(args.output_dir, args.r48_identity) else 1


if __name__ == '__main__':
    raise SystemExit(main())
