#!/usr/bin/env python3
"""Closed-roster API36 synthetic receipt: only redacted metadata leaves the runner."""
import argparse
import json
import re
from pathlib import Path

ROSTER = {
    "com.sdvsync.mods.CbNx02DownloadUxDeviceTest": {
        "approvalCanBeDisabledAndRestored", "queuedReviewPreservesExactFileIdsAndPromotesNext",
        "journalRetainsFileIdentityWithoutBearerUrl", "stagedArchiveChecksumRejectsTamperingWithoutInstalling",
        "terminalInstallIsNotOverwrittenByServiceCancellation",
    },
    "com.sdvsync.ui.screens.CbNx02DownloadsUiDeviceTest": {
        "exactFileReviewCardOpensRealReviewRoute", "activeCardShowsBytesAndExplicitCancelAllAction",
        "backlogCardCannotApproveDifferentFile",
    },
    "com.sdvsync.ui.screens.CbNx02BQueueControlsUiDeviceTest": {
        "queuedCardMovesAndCancelsOnlyItsOwnJob", "pausedCardCanResumeWithoutSecondAdmission",
        "interruptedCardCannotResumeWithoutNewNexusLink",
    },
    "com.sdvsync.mods.CbNx02BAdmissionDeviceTest": {
        "allProtectedNexusStatesRefuseDuplicateAdmission", "differentExactFileCanAdmitWithoutModLevelLock",
        "multipleJournalInstancesAdmitSameFileOnlyOnce",
        "crashDuringInstallationIsVerifyOnlyEvenWithApprovalOff",
        "durableReviewReceiptBlocksAdmissionEvenWithoutJournalRow",
        "terminalAndUncertainStatesRejectLateWorkerWrites",
    },
}
EXPECTED = {(c, t) for c, tests in ROSTER.items() for t in tests}

def completed_tests(raw: str):
    current_class = None
    current_test = None
    passed = []
    for line in raw.replace('\r', '').splitlines():
        m = re.fullmatch(r'INSTRUMENTATION_STATUS: class=(.+)', line.strip())
        if m: current_class = m.group(1).strip()
        m = re.fullmatch(r'INSTRUMENTATION_STATUS: test=(.+)', line.strip())
        if m: current_test = m.group(1).strip()
        m = re.fullmatch(r'INSTRUMENTATION_STATUS_CODE: (-?\d+)', line.strip())
        if m and m.group(1) == '0' and current_class and current_test:
            passed.append((current_class, current_test))
            current_class = current_test = None
    return passed

def validate(raw, code, source, app_sha, installed_sha, test_sha):
    passed = completed_tests(raw)
    marker = re.findall(r'OK \((\d+) tests?\)', raw)
    shavalid = all(re.fullmatch('[0-9a-f]{40}', v) for v in (source,)) and all(
        re.fullmatch('[0-9a-f]{64}', v) for v in (app_sha, installed_sha, test_sha))
    return (code == 0 and shavalid and app_sha == installed_sha and
        len(passed) == len(EXPECTED) and set(passed) == EXPECTED and
        len(set(passed)) == len(passed) and marker == [str(len(EXPECTED))] and
        not any(v in raw for v in ('FAILURES!!!', 'INSTRUMENTATION_FAILED', 'INSTRUMENTATION_RESULT: shortMsg=')))

def main():
    p = argparse.ArgumentParser()
    for v in ('log', 'exit-code', 'source', 'run', 'app-sha', 'installed-sha', 'test-sha', 'output'):
        p.add_argument('--'+v, required=True)
    a = p.parse_args()
    raw = Path(a.log).read_text(encoding='utf8', errors='replace')
    ok = validate(raw, int(a.exit_code), a.source, a.app_sha, a.installed_sha, a.test_sha)
    # The receipt does not contain raw instrumentation, URLs, credentials or filesystem paths.
    receipt = {'schema_version': 2, 'qualification': 'CBNX02B_HF02_API36_SYNTHETIC',
        'status': 'PASS' if ok else 'FAIL', 'source_sha': a.source, 'run_id': a.run,
        'test_count': len(EXPECTED) if ok else 0,
        'test_classes': sorted(ROSTER) if ok else [],
        'apk_sha256': a.app_sha, 'test_apk_sha256': a.test_sha,
        'emulator_only': True, 'live_nexus_qualified': False,
        'physical_device_qualified': False, 'release_qualified': False,
        'secrets_in_receipt': False}
    Path(a.output).write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    if not ok: raise SystemExit('CBNX02B_HF02_HOSTED_INSTRUMENTATION_REFUSED')
    print('CBNX02B_HF02_INSTRUMENTATION_ROSTER_PASS')

if __name__ == '__main__': main()
