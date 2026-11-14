#!/usr/bin/env python3
"""LAB03A fail-closed source gate; source contract is not physical acceptance."""
from pathlib import Path
import re,sys
if sys.flags.optimize:raise SystemExit('LAB03A_PYTHON_OPTIMIZATION_FORBIDDEN')
ROOT=Path(__file__).resolve().parents[2]
class Refused(Exception):pass

def require(ok,why):
    if not ok:raise Refused(why)

def check(root=ROOT):
    files={
      'evidence':'app/src/main/java/com/sdvsync/mods/NexusLab03Evidence.kt',
      'ui':'app/src/main/java/com/sdvsync/ui/screens/NexusPairingPanel.kt',
      'test':'app/src/androidTest/java/com/sdvsync/mods/CbNxLab03DeviceTest.kt',
      'gradle':'app/build.gradle.kts',
      'runner':'scripts/devtool/cbnx06_lab03_emulator_ci.sh',
      'receipt':'scripts/devtool/cbnx06_lab03_receipt.py',
      'workflow':'.github/workflows/cbnx06-lab03-synthetic.yml',
    }
    texts={}
    for key,path in files.items():
        f=root/path
        require(f.is_file() and not f.is_symlink(),'LAB03A_MISSING_OR_LINKED_SOURCE:'+path)
        texts[key]=f.read_text()
    e=texts['evidence']
    for anchor in (
        'check(BuildConfig.CBNX_LAB && context.packageName == LAB_PACKAGE)',
        'private const val LAB_PACKAGE = "com.sdvsync.cbnx06lab"',
        'private const val SCOPE = "LAB_SYNTHETIC_ONLY"',
        'CinderboxLabBoundary.requirePrivate(directory)',
        'CinderboxLabBoundary.requirePrivate(archiveFile)',
        'CinderboxLabBoundary.requirePrivate(receiptFile)',
        'CinderboxLabBoundary.requireModsRoot(mods)',
        'ModFileManager(context, ModManifestParser()).previewFromZip(archiveFile)',
        'check(before == after) { "LAB03_PREVIEW_MUTATED_MODS" }',
        '.put("nexus_file_provenance_verified", false)',
        '.put("installed", false)',
        'LAB03_ARCHIVE_CHANGED','LAB03_RECEIPT_CHANGED',
        'LAB03_ARCHIVE_DURABILITY_MISMATCH','LAB03_RECEIPT_DURABILITY_MISMATCH',
    ):require(anchor in e,'LAB03A_EVIDENCE_GUARD_MISSING:'+anchor)
    for forbidden in ('ModDownloadService.start(', 'installFromZip(', 'NexusPairingInbox.admit(',
                      'getDownloadUrl(', 'android.permission.MANAGE_EXTERNAL_STORAGE',
                      '/storage/emulated/0/StardewValley', 'su -c', 'Runtime.getRuntime'):
        require(forbidden not in e,'LAB03A_SYNTHETIC_CAPABILITY_FORBIDDEN:'+forbidden)
    # HF04: use the same canonical filesDir as CinderboxLabBoundary.privateHome.
    # Do not relax requirePrivate() to accept arbitrary symlink aliases.
    require('val directory = File(context.filesDir.canonicalFile, FOLDER)' in e and
            'File(context.filesDir, FOLDER)' not in e,
            'LAB03A_HF04_NONCANONICAL_EVIDENCE_ROOT')
    ui=texts['ui']
    require("""if (BuildConfig.CBNX_LAB) {
            Text("LAB03A synthetic only""" in ui, 'LAB03A_UI_SYNTHETIC_BRANCH_UNGUARDED')
    for anchor in ('if (BuildConfig.CBNX_LAB)', 'NexusLab03Evidence.previewSynthetic(context)',
                   'cbnx06.lab03a.preview-synthetic', 'LAB03A synthetic only',
                   'Enter this code in the LAB02C Firefox popup (port 38472).',
                   'Not downloaded from Nexus'):
        require(anchor in ui,'LAB03A_UI_GUARD_MISSING:'+anchor)
    require('if (providers.gradleProperty("cbnxLabAndroidTest").orNull == "true") "cbnxLab" else "debug"' in texts['gradle'],
            'LAB03A_TEST_BUILD_VARIANT_MISSING')
    require('com.sdvsync.mods.CbNxLab03DeviceTest' in texts['runner'] and
            'com.sdvsync.cbnx06lab.test/androidx.test.runner.AndroidJUnitRunner' in texts['runner'] and
            'ro.kernel.qemu' in texts['runner'] and 'test -z ' in texts['runner'],
            'LAB03A_EMULATOR_RUNNER_GUARDS_MISSING')
    require('INSTRUMENTATION_CODE: -1' in texts['receipt'] and
            'live_nexus_qualified' in texts['receipt'] and
            'production_data_immutability_qualified' in texts['receipt'],
            'LAB03A_RECEIPT_UNQUALIFIED')
    for anchor in ('-PcbnxLabAndroidTest=true', ':app:assembleCbnxLabAndroidTest',
                   'cbnx06_lab03_tests.py', 'ReactiveCircus/android-emulator-runner',
                   'api-level: 36','cbnx06_lab03_emulator_ci.sh'):
        require(anchor in texts['workflow'],'LAB03A_HOSTED_GATE_MISSING:'+anchor)
    t=texts['test']
    for anchor in ('@Test fun syntheticArchivePreviewDoesNotModifyLabMods()',
                   '@Test fun labPairingRequiresConsentAndRecordsOnlyExactInboxRequest()',
                   '38472','getBoolean("download_started")',
                   'getBoolean("archive_staged")','NexusPairingInbox.resolve('):
        require(anchor in t,'LAB03A_DEVICE_COVERAGE_MISSING:'+anchor)
    # LAB03A HF01: the lab-only tests have to compile against the inherited
    # debug synthetic worker class, without importing its debug-only manifest.
    require('getByName("cbnxLab").java.srcDir("src/debug/java")' in texts['gradle'],
            'LAB03A_HF01_INHERITED_DEBUG_SYNTHETIC_WORKER_NOT_SHARED')
    # A copied durability check accidentally appeared here, outside its helper
    # scope. The real private archive durability witness must remain in evidence.
    require('check(archiveFile.isFile' not in t and 'sha256(archiveFile.readBytes())' not in t,
            'LAB03A_HF01_UNBOUND_KOTLIN_ARCHIVE_LOCALS')
    require(t.count('@Test fun ') == 2, 'LAB03A_HF01_UNEXPECTED_INSTRUMENTATION_ROSTER')
    print('CBNX06_LAB03A_HF01_COMPILE_CONTRACT_PASS')
    for marker in ('#syntheticArchivePreviewDoesNotModifyLabMods',
                   '#labPairingRequiresConsentAndRecordsOnlyExactInboxRequest',
                   '--raw-pair', '--exit-pair', 'timeout 90s adb',
                   'trap \'rm -f -- "$raw" "$raw_pair"\' EXIT'):
        require(marker in texts['runner'], 'LAB03A_HF02_RUNNER_DIAGNOSTIC_MISSING:'+marker)
    for marker in ('def case_status(', 'def verify_split(', 'def safe_failure_location(',
                   "'TEST_ASSERTION_FAILED'", "'TEST_EVENTS_MISSING'",
                   "'production_data_immutability_qualified':False", 'failure_site'):
        require(marker in texts['receipt'], 'LAB03A_HF02_RECEIPT_DIAGNOSTIC_MISSING:'+marker)
    print('CBNX06_LAB03A_HF02_CASE_DIAGNOSTIC_SOURCE_PASS')
    print('CBNX06_LAB03A_SYNTHETIC_PAIRING_SOURCE_GATE_PASS')
if __name__=='__main__':
    try:check()
    except (Refused,OSError) as e:print('CBNX06_LAB03A_REFUSED:'+str(e),file=sys.stderr);sys.exit(2)
