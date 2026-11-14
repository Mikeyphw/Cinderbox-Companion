#!/usr/bin/env python3
"""LAB06B strict source contracts; negative synthetic emulator only, never physical."""
from __future__ import annotations
from pathlib import Path
import re,sys
ROOT=Path(__file__).resolve().parents[2]
PATHS=(
 'app/src/androidTest/java/com/sdvsync/mods/CbNxLab06bNegativeDeviceTest.kt',
 'scripts/devtool/cbnx06_lab06b_emulator_ci.sh',
 'scripts/devtool/cbnx06_lab06b_receipt.py',
 '.github/workflows/cbnx06-lab06b-negative-matrix.yml',
 '.github/workflows/cbnx06-full-cinderbox-lab.yml',
 'docs/CBNX06_LAB06B_HOSTED_NEGATIVE_MATRIX.md',
 'app/src/main/java/com/sdvsync/mods/NexusLab04SyntheticTransaction.kt',
 'app/src/main/java/com/sdvsync/mods/NexusLab03DArchiveStage.kt',
)
EXPECTED=(
 'changedArchiveBytesCannotReachMods',
 'forgedNexusProvenanceCannotReachMods',
 'incorrectApprovalKeyCannotReachMods',
 'interruptedIntentRequiresManualReview',
 'completedRollbackCannotReplayOrReinstall',
)
class Refused(ValueError):pass
def need(ok,why):
    if not ok:raise Refused('LAB06B_'+why)

def validate(test,runner,receipt,workflow,full,doc,transaction,stage):
    methods=re.findall(r'@Test fun (\w+)\(\)',test)
    need(tuple(methods)==EXPECTED,'FIVE_CASE_ROSTER_DRIFT')
    need('@Before fun isolatedAndClean()' in test and
         'CinderboxLabBoundary.initialize(context)' in test and
         'CinderboxLabBoundary.requireModsRoot(mods())' in test and
         'assertPrivateAndEmpty()' in test and
         'assertFalse("LAB06B_STALE_JOURNAL", journal().exists())' in test,
         'LAB_ISOLATION_GUARD_MISSING')
    for marker in ('BuildConfig.CBNX_LAB','BuildConfig.APPLICATION_ID',
        'context.packageName', 'NexusLab03DArchiveStage.stageSynthetic(context)',
        'zip.appendBytes(byteArrayOf(1))',
        'record.put("nexus_file_provenance_verified", true)',
        'manager.installFromZip(zip, "LAB06B_INVALID_APPROVAL_KEY")',
        'result is InstallResult.Error', '"INSTALLING"',
        'NexusLab04SyntheticTransaction.installSynthetic(context)',
        'NexusLab04SyntheticTransaction.rollbackSynthetic(context)',
        '"ROLLED_BACK"', 'assertPrivateAndEmpty()',
        'catch (e: IllegalStateException)', 'catch (e: IllegalArgumentException)',
        'fail("LAB06B_EXPECTED_REFUSAL")'):
        need(marker in test,'TEST_SAFETY_GUARD_MISSING:'+marker)
    need(test.count('.put("state", "INSTALLING")')==1, 'INTERRUPTED_JOURNAL_FIXTURE_DRIFT')
    need(test.count('refuse { NexusLab04SyntheticTransaction.installSynthetic(context) }')==4,
         'INSTALL_REFUSAL_CASE_COUNT_DRIFT')
    need(test.count('refuse { NexusLab04SyntheticTransaction.rollbackSynthetic(context) }')==2,
         'ROLLBACK_REFUSAL_CASE_COUNT_DRIFT')
    for bad in ('/storage/emulated/0/StardewValley','/sdcard/', 'su -c',
                'ModDownloadService(', 'getDownloadUrl(', 'NexusPairingBridge.start(',
                'http://','https://','deleteRecursively()', 'System.exit('):
        need(bad not in test,'FORBIDDEN_DEVICE_TEST_CAPABILITY:'+bad)
    for marker in ('ro.kernel.qemu','ro.build.version.sdk','" = 36',
        'shell pm path com.sdvsync 2>/dev/null',
        'adb -s "$serial" shell pm clear com.sdvsync.cbnx06lab',
        'test "$cleared" = Success', 'test "${#app[@]}" = 1',
        'test "${#test_apk[@]}" = 1',
        'com.sdvsync.cbnx06lab.test/androidx.test.runner.AndroidJUnitRunner',
        'timeout 180s', 'trap \'rm -rf -- "$rawdir"\' EXIT',
        'CBNX_LAB06B_HEAD_SHA', 'cbnx06_lab06b_receipt.py',
        'LAB06B_API36_FIVE_NEGATIVE_CASES_PASS_PHYSICAL_DEFERRED'):
        need(marker in runner,'RUNNER_GUARD_MISSING:'+marker)
    need(runner.count('pm clear com.sdvsync.cbnx06lab')==1 and
         'pm clear com.sdvsync ' not in runner and
         'pm uninstall' not in runner and 'adb -s "$serial" root' not in runner,
         'LAB_CLEAR_SCOPE_BROKEN')
    need(runner.count('CbNxLab06bNegativeDeviceTest#$method')==1,
         'RUNNER_MISSING_EXACT_CLASS')
    for method in EXPECTED:
        need(method in runner and method in receipt,'CASE_NOT_RECORDED:'+method)
    for marker in ('actual_test_count', 'tests_passed',
                   'events.count' if False else 'event.count(name) == 2',
                   "'OK (1 test)' in raw", "'INSTRUMENTATION_CODE: -1' in raw",
                   "'INSTRUMENTATION_STATUS_CODE: -2' not in raw",
                   "'physical_qualified':False", "'live_iceraven_qualified':False",
                   "'release_qualified':False",'SAFE_FRAME','FAILURE_MARKERS',
                   'if data[\'status\']!=\'PASS\''):
        need(marker in receipt,'RECEIPT_CONTRACT_MISSING:'+marker)
    need(workflow.count('test "$(git rev-parse HEAD)" = "$CBNX_LAB06B_HEAD_SHA"')==2, 'CI_HEAD_PIN_COUNT_DRIFT')
    for marker in ('persist-credentials: false',
                   'test "$(git rev-parse HEAD)" = "$CBNX_LAB06B_HEAD_SHA"',
                   '-PcbnxLabAndroidTest=true',
                   ':app:assembleCbnxLab :app:assembleCbnxLabAndroidTest',
                   'api-level: 36', 'cbnx06_lab06b_emulator_ci.sh',
                   'cbnx06-lab06b-negative-matrix-api36-receipt',
                   'cbnx06_lab05_tests.py', 'cbnx06_lab04_source_gate.py'):
        need(marker in workflow,'CI_CONTRACT_MISSING:'+marker)
    for marker in ("      - 'scripts/devtool/cbnx06_lab06b_*.py'",
                   "      - 'app/src/androidTest/java/com/sdvsync/mods/CbNxLab06bNegativeDeviceTest.kt'",
                   'python3 -B scripts/devtool/cbnx06_lab06b_source_gate.py',
                   'python3 -B scripts/devtool/cbnx06_lab06b_tests.py',
                   'python3 -B scripts/devtool/cbnx06_lab05_tests.py',
                   ':app:assembleCbnxLab'):
        need(marker in full,'FULL_LAB_GATE_MISSING:'+marker)
    for marker in ('Synthetic only', 'physical', 'not Nexus', 'five',
                   'private', 'approval', 'replay', 'readiness'):
        need(marker.lower() in doc.lower(),'DOCUMENT_SCOPE_MISSING:'+marker)
    need('CinderboxLabBoundary.requireModsRoot(mods)' in transaction and
         'NexusLab03DArchiveStage.stageSynthetic(context)' in transaction and
         'NexusLab03DArchivePolicy.PROVENANCE' in transaction,
         'EXISTING_TRANSACTION_SAFETY_LOST')
    need('CinderboxLabBoundary.requirePrivate(file)' in stage and
         'check(before == snapshot())' in stage and
         '!previous.getBoolean("nexus_file_provenance_verified")' in stage,
         'EXISTING_STAGING_SAFETY_LOST')
    return True

def main():
    inputs=[]
    for path in PATHS:
        p=ROOT/path
        need(p.is_file() and not p.is_symlink(),'MISSING_OR_LINKED_SOURCE:'+path)
        inputs.append(p.read_text(encoding='utf8'))
    validate(*inputs)
    print('LAB06B_SOURCE_FIVE_NEGATIVE_CASES_AND_PRIVATE_API36_GATES_PASS')

if __name__=='__main__':
    try:main()
    except (Refused,OSError) as exc:
        print('LAB06B_REFUSED '+str(exc),file=sys.stderr)
        raise SystemExit(2)
