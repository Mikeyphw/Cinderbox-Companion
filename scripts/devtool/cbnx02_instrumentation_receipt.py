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
        "exactJobEvidenceButtonCannotStartInstallOrOpenWrongMod",
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

def validate(raw, code, source, app_sha, installed_sha, test_sha):
    # AndroidJUnitRunner supplies one start and one completion per named method.
    # Duplicate or missing starts, forged completions and unknown statuses fail closed.
    started, passed = {}, {}
    events, invalid = 0, 0
    block = {}
    for line in raw.replace('\r', '').splitlines():
        if line.startswith('INSTRUMENTATION_STATUS: '):
            value = line[len('INSTRUMENTATION_STATUS: '):]
            key, sep, content = value.partition('=')
            if sep and key in ('class', 'test', 'numtests'):
                block[key] = content.strip()
        elif line.startswith('INSTRUMENTATION_STATUS_CODE: '):
            events += 1
            code_str = line.split(': ', 1)[1].strip()
            pair = (block.get('class'), block.get('test'))
            if pair not in EXPECTED or block.get('numtests') != str(len(EXPECTED)):
                invalid += 1
            elif code_str == '1':
                started[pair] = started.get(pair, 0) + 1
            elif code_str == '0':
                passed[pair] = passed.get(pair, 0) + 1
            else:
                invalid += 1
            block = {}
    marker = re.findall(r'OK \((\d+) tests?\)', raw)
    shavalid = bool(re.fullmatch('[0-9a-f]{40}', source)) and all(
        re.fullmatch('[0-9a-f]{64}', v) for v in (app_sha, installed_sha, test_sha))
    return (code == 0 and shavalid and app_sha == installed_sha and invalid == 0 and
        events == 2 * len(EXPECTED) and len(started) == len(EXPECTED) and
        len(passed) == len(EXPECTED) and all(started.get(x) == 1 and passed.get(x) == 1
        for x in EXPECTED) and marker == [str(len(EXPECTED))] and
        'INSTRUMENTATION_CODE: -1' in raw and
        not any(v in raw for v in ('FAILURES!!!', 'INSTRUMENTATION_FAILED',
            'INSTRUMENTATION_RESULT: shortMsg=')))


def main():
    p = argparse.ArgumentParser()
    for v in ('log', 'exit-code', 'source', 'run', 'app-sha', 'installed-sha', 'test-sha', 'output'):
        p.add_argument('--'+v, required=True)
    a = p.parse_args()
    raw = Path(a.log).read_text(encoding='utf8', errors='replace')
    ok = validate(raw, int(a.exit_code), a.source, a.app_sha, a.installed_sha, a.test_sha)
    # The receipt does not contain raw instrumentation, URLs, credentials or filesystem paths.
    receipt = {'schema_version': 2, 'qualification': 'CBNX05A_API36_EXACT_JOB_EVIDENCE',
        'status': 'PASS' if ok else 'FAIL', 'source_sha': a.source, 'run_id': a.run,
        'test_count': len(EXPECTED) if ok else 0,
        'event_count': 2 * len(EXPECTED) if ok else 0,
        'expected_event_count': 2 * len(EXPECTED),
        'test_classes': sorted(ROSTER) if ok else [],
        'apk_sha256': a.app_sha, 'test_apk_sha256': a.test_sha,
        'emulator_only': True, 'live_nexus_qualified': False,
        'physical_device_qualified': False, 'release_qualified': False,
        'secrets_in_receipt': False}
    Path(a.output).write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    if not ok: raise SystemExit('CBNX02B_HF02_HOSTED_INSTRUMENTATION_REFUSED')
    print('CBNX02B_HF02_INSTRUMENTATION_ROSTER_PASS')

if __name__ == '__main__': main()
