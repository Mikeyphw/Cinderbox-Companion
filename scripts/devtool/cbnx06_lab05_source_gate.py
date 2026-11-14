#!/usr/bin/env python3
"""LAB05 hosted Android UI acceptance: exact source, actual test count and isolation gates."""
from __future__ import annotations
from pathlib import Path
import re, sys
ROOT=Path(__file__).resolve().parents[2]
class Refused(ValueError):pass

def need(ok, why):
    if not ok: raise Refused('LAB05_'+why)

def validate(test,runner,receipt,workflow,full,gradle,panel,transaction):
    methods=re.findall(r'@Test fun (\w+)\(\)',test)
    expected=(
      'unpairedConsentRemainsDisabledAfterWindowStart',
      'cancelSyntheticInstallDoesNotWriteModsOrJournal',
      'exactFileCancelKeepsRequestPendingWithoutBrowserLaunch',
      'userConfirmedSyntheticInstallAndRollbackRestoresEmptyLabRoot')
    need(tuple(methods)==expected,'INSTRUMENTATION_ROSTER_DRIFT')
    # HF01: Compose test node assertion methods do not have standalone import symbols.
    # The failed hosted AndroidTest Kotlin compilation (run 43555864406) proves that
    # importing either symbol is invalid for this AndroidX Compose test version.
    for forbidden_import in (
        'import androidx.compose.ui.test.assertDoesNotExist',
        'import androidx.compose.ui.test.assertExists',
    ):
        need(forbidden_import not in test,'HF01_INVALID_COMPOSE_ASSERTION_IMPORT:'+forbidden_import)
    need(test.count('.assertExists()') >= 4 and
         test.count('.assertDoesNotExist()') == 2,
         'HF01_NODE_ASSERTIONS_REMOVED')
    for marker in ('assertTrue("LAB05_DEBUG_BUILD_REFUSED", BuildConfig.CBNX_LAB)',
      'assertEquals("com.sdvsync.cbnx06lab", context.packageName)',
      'CinderboxLabBoundary.initialize(context)',
      'CinderboxLabBoundary.requireModsRoot(mods())',
      'NexusPairingPanel()',
      'cbnx03b.pairing.allow-handoff', 'assertIsNotEnabled()',
      'cbnx06.lab04.confirm-action', 'cbnx06.lab04.cancel-action',
      'assertFalse(journal().exists())',
      'NexusPairingInbox.admit(context, id, "995000001", file)',
      'cbnx06.lab03c.cancel-open',
      'NexusLab04SyntheticPolicy.FOLDER',
      '"INSTALLED"', '"ROLLED_BACK"', 'mods().listFiles()?.isEmpty() == true',
      'rule.waitUntil(90000)'):
        need(marker in test,'UI_TEST_GUARD_MISSING:'+marker)
    need(test.count('rule.onNodeWithTag("cbnx03b.pairing.allow-handoff").performScrollTo().assertIsNotEnabled()')==2, 'CONSENT_ASSERTION_COUNT_DRIFT')
    for forbidden in ('/storage/emulated/0/StardewValley', 'nxm://','getDownloadUrl(',
                      'su -c','ModDownloadService(', 'deleteRecursively()'):
        need(forbidden not in test,'UNSAFE_TEST:'+forbidden)
    for marker in ('ro.kernel.qemu','ro.build.version.sdk','= 36',
                   'test -z "$(adb -s "$serial" shell pm path com.sdvsync'):
        need(marker in runner,'EMULATOR_BOUNDARY_MISSING:'+marker)
    for marker in ('trap \'rm -rf -- "$rawdir"\' EXIT',
                   'timeout 180s', 'CbNxLab05UiJourneyTest#',
                   'cbnx06_lab05_receipt.py', 'CBNX_LAB05_HEAD_SHA',
                   'com.sdvsync.cbnx06lab.test/androidx.test.runner.AndroidJUnitRunner',
                   'CBNX06_LAB05_API36_COMPOSE_JOURNEYS_PASS_PHYSICAL_DEFERRED'):
        need(marker in runner,'RUNNER_GUARD_MISSING:'+marker)
    for name in expected:need(name in runner and name in receipt,'MISSING_RECORDED_CASE:'+name)
    for marker in ("'OK (1 test)' in raw", "'INSTRUMENTATION_CODE: -1' in raw",
                   'events.count(name)==2', "'INSTRUMENTATION_STATUS_CODE: -2' not in raw",
                   "'physical_qualified':False", "'live_iceraven_qualified':False",
                   "'release_qualified':False", "'actual_test_count':len(results)",
                   'SAFE_FRAME', 'if data[\'status\']!=\'PASS\''):
        need(marker in receipt,'RECEIPT_CONTRACT_MISSING:'+marker)
    for marker in ('test "$(git rev-parse HEAD)" = "$CBNX_LAB05_HEAD_SHA"',
                   'persist-credentials: false','api-level: 36',
                   ':app:assembleCbnxLab :app:assembleCbnxLabAndroidTest',
                   '-PcbnxLabAndroidTest=true','cbnx06_lab05_emulator_ci.sh',
                   'cbnx06-lab05-hosted-ui-api36-receipt'):
        need(marker in workflow,'HOSTED_WORKFLOW_MISSING:'+marker)
    need(workflow.count('test "$(git rev-parse HEAD)" = "$CBNX_LAB05_HEAD_SHA"')==2, 'HOSTED_SOURCE_PIN_COUNT_DRIFT')
    for marker in ("      - 'scripts/devtool/cbnx06_lab05_*.py'",
                   'python3 -B scripts/devtool/cbnx06_lab05_source_gate.py',
                   'python3 -B scripts/devtool/cbnx06_lab05_tests.py'):
        need(marker in full,'FULL_LAB_INHERITANCE_MISSING:'+marker)
    need('NexusLab04SyntheticTransaction.installSynthetic(context)' in panel and
         'NexusLab04SyntheticTransaction.rollbackSynthetic(context)' in panel,
         'LAB04_UI_HOOK_LOST')
    need('CinderboxLabBoundary.requireModsRoot(mods)' in transaction and
         'NexusLab03DArchiveStage.stageSynthetic(context)' in transaction,
         'PRIVATE_SYNTHETIC_TRANSACTION_LOST')
    # HF02: createComposeRule requires the Compose test host in the *custom* LAB
    # build type, not only in debug. The host must be present in the installed LAB APK.
    need('add("cbnxLabImplementation", "androidx.compose.ui:ui-test-manifest")' in gradle,
         'HF02_LAB_COMPOSE_HOST_DEPENDENCY_MISSING')
    need('debugImplementation("androidx.compose.ui:ui-test-manifest")' in gradle,
         'HF02_ORIGINAL_DEBUG_HOST_MISSING')
    need('createComposeRule()' in test,
         'HF02_HOST_RULE_TEST_MISMATCH')
    for marker in ('aapt', 'dump xmltree', 'AndroidManifest.xml',
                   'androidx.compose.ui.test.junit4.android.AndroidComposeTestActivity',
                   'LAB05_HF02_REFUSED_COMPOSE_HOST_ACTIVITY_ABSENT',
                   'LAB05_HF02_COMPOSE_HOST_ACTIVITY_PRESENT'):
        need(marker in runner,'HF02_HOSTED_MANIFEST_PREFLIGHT_MISSING:'+marker)
    for marker in ('SAFE_DIAGNOSTIC_CATEGORIES', 'diagnostic_category',
                   "'failure_category':diagnostic_category(raw)"):
        need(marker in receipt, 'HF02_SAFE_FAILURE_CATEGORY_MISSING:'+marker)
    need('"cbnxLab" else "debug"' in gradle and
         'getByName("cbnxLab").java.srcDir("src/debug/java")' in gradle,
         'LAB_ANDROID_TEST_VARIANT_MISSING')
    return True

PATHS=(
 'app/src/androidTest/java/com/sdvsync/ui/screens/CbNxLab05UiJourneyTest.kt',
 'scripts/devtool/cbnx06_lab05_emulator_ci.sh',
 'scripts/devtool/cbnx06_lab05_receipt.py',
 '.github/workflows/cbnx06-lab05-hosted-ui.yml',
 '.github/workflows/cbnx06-full-cinderbox-lab.yml',
 'app/build.gradle.kts',
 'app/src/main/java/com/sdvsync/ui/screens/NexusPairingPanel.kt',
 'app/src/main/java/com/sdvsync/mods/NexusLab04SyntheticTransaction.kt')

def main():
    text=[]
    for path in PATHS:
        p=ROOT/path
        need(p.is_file() and not p.is_symlink(),'UNSAFE_FILE:'+path)
        text.append(p.read_text())
    validate(*text)
    print('CBNX06_LAB05_UI_ROSTER_4_EMULATOR_PRIVATE_AND_RECEIPT_GATES_PASS')
if __name__=='__main__':
    try:main()
    except (Refused,OSError) as e:
        print('CBNX06_LAB05_REFUSED '+str(e),file=sys.stderr);sys.exit(2)
