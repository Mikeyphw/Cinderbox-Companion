#!/usr/bin/env python3
"""NEX-R3 HF01 — fail-closed runtime diagnostics, no production changes."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST = 'app/src/androidTest/java/com/sdvsync/ui/ux/NexR3NativeJourneyTest.kt'
RUNNER = 'scripts/devtool/nex_r3_emulator_ci.sh'
WORKFLOW = '.github/workflows/nex-r3-real-native-journey.yml'
POLICY = 'docs/security/M3_RELEASE_POLICY.json'


def check(root: Path = ROOT) -> list[str]:
    root = Path(root)
    def read(name):
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError('NEX_R3_HF01_FILE_MISSING_OR_SYMLINK:' + name)
        return path.read_text(encoding='utf-8')
    test, runner, ci = read(TEST), read(RUNNER), read(WORKFLOW)
    policy = json.loads(read(POLICY))
    expected = {
        'named text wait': 'NEX_R3_TEXT_TIMEOUT:' in test and '35000L' in test,
        'named tag wait': 'NEX_R3_TAG_TIMEOUT:' in test,
        'named offset wait': 'NEX_R3_OFFSET_TIMEOUT:' in test and 'waitForPageOffset50()' in test,
        'real tests retained': all(t in test for t in (
            'realMainActivityDiscoverPagingDetailReviewAndBack',
            'authRateLimitAndServiceFailuresStayReadOnly',
            'noNexusKeyKeepsLocalModsRouteAvailable',
            'assertNoDownloadRequests()', 'RuleChain.outerRule(fixture).around(compose)')),
        'sanitized diagnostics': all(t in runner for t in (
            'diagnostic-$width.txt', 'NEX_R3_SANITIZED_FAILURE_DIAGNOSTIC',
            'INSTRUMENTATION_STATUS: (class|test|current|numtests)',
            'COMPOSE_TIMEOUT_EXCEPTION', 'NexR3NativeJourneyTest',
            'NEX_R3_HOSTED_INSTRUMENTATION_REFUSED')),
        'snapshot preservation': 'for stage in discover page-two detail file-review returned' in runner,
        'offline and source pin': all(t in runner for t in (
            'r48_offline_gate.py', 'ro.kernel.qemu', 'GITHUB_SHA',
            'font_scale 1.0', 'OK (3 tests)', 'nex_r3_evidence.py')),
        'CI source checks': all(t in ci for t in (
            'nex_r3_hf01_gate.py', 'test_nex_r3_hf01_gate.py',
            'assembleDebugAndroidTest', 'android-emulator-runner@')),
    }
    errors = ['NEX_R3_HF01_MISSING:' + k for k, passed in expected.items() if not passed]
    for key in ('release_enabled', 'publication_enabled', 'automatic_device_install', 'device_qualification_complete'):
        if policy.get(key) is not False:
            errors.append('NEX_R3_HF01_RELEASE_POLICY_CHANGED:' + key)
    for token in ('CINDERBOX_NEXUS_API_KEY', 'getDownloadUrl(', 'startDownload(',
                  'requestShizukuPermission(', 'WebView('):
        if token in test + runner + ci:
            errors.append('NEX_R3_HF01_FORBIDDEN:' + token)
    return errors

if __name__ == '__main__':
    try: issues=check()
    except (ValueError, OSError) as e: raise SystemExit('NEX_R3_HF01_REFUSED:' + str(e))
    if issues: raise SystemExit('\n'.join(issues))
    print('NEX_R3_HF01_SOURCE_DIAGNOSTICS_AND_SAFETY_PASS')
