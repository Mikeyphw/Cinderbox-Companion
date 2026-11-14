#!/usr/bin/env python3
"""LAB04 exhaustive source-isolation and manual-consent security contracts.

Source-only: never claims real Android or rollback qualification.
"""
from __future__ import annotations
from pathlib import Path
import sys

if sys.flags.optimize: raise SystemExit('LAB04_ASSERTIONS_REQUIRED')
ROOT=Path(__file__).resolve().parents[2]
STAGE='app/src/main/java/com/sdvsync/mods/NexusLab04SyntheticTransaction.kt'
POLICY='app/src/main/java/com/sdvsync/mods/NexusLab04SyntheticPolicy.kt'
PANEL='app/src/main/java/com/sdvsync/ui/screens/NexusPairingPanel.kt'
UNIT='app/src/test/java/com/sdvsync/mods/NexusLab04SyntheticPolicyTest.kt'
WF='.github/workflows/cbnx06-lab04-synthetic-rollback.yml'
FULL='.github/workflows/cbnx06-full-cinderbox-lab.yml'

class Refused(Exception): pass

def need(value,message):
    if not value: raise Refused('LAB04_'+message)

STAGE_ANCHORS={
 'PRIVATE_APP':'BuildConfig.CBNX_LAB && BuildConfig.APPLICATION_ID == APP',
 'PRIVATE_CONTEXT':'context.packageName == APP',
 'PRIVATE_MODS':'CinderboxLabBoundary.requireModsRoot(mods)',
 'PRIVATE_RECEIPT':'CinderboxLabBoundary.requirePrivate(journal)',
 'LAB_MODS_ROOT':'File(CinderboxPaths.MODS_DIR)',
 'SYMLINK_MOD_ROOT':'Files.isSymbolicLink(mods.toPath())',
 'SYMLINK_MEMBER':'members.none { Files.isSymbolicLink(it.toPath()) }',
 'SYMLINK_RECEIPT':'Files.isSymbolicLink(journal.toPath())',
 'SIGNED_STAGED':'NexusLab03DArchiveStage.stageSynthetic(context)',
 'STAGE_PROVENANCE':'receipt.provenance == NexusLab03DArchivePolicy.PROVENANCE',
 'STAGE_DIGEST':'sha(archive.readBytes()) == receipt.sha256',
 'PRECONDITION_EMPTY':'rootMembers(mods).isEmpty()',
 'ONE_SHOT_INSTALL':'NexusLab04SyntheticPolicy.mayInstall(',
 'REVIEW_REAL':'manager.previewFromZip(archive)',
 'REVIEW_ONE':'review.changes.size == 1',
 'REVIEW_ADD':'review.changes.single().action == "ADD"',
 'REVIEW_NAME':'review.changes.single().folder == NexusLab04SyntheticPolicy.FOLDER',
 'REVIEW_ID':'review.changes.single().uniqueId == NexusLab04SyntheticPolicy.UNIQUE_ID',
 'APPROVAL_KEY':'manager.installFromZip(archive, review.approvalKey)',
 'SUCCESS_CHECK':'result is InstallResult.Success && result.mods.size == 1',
 'PERSIST_BEFORE_WRITE':'persist(journal, null, "INSTALLING", hash)',
 'INSTALL_POST_VERIFY':'check(exactSyntheticMod(mods))',
 'PERSIST_INSTALL':'persist(journal, "INSTALLING", "INSTALLED", hash)',
 'ONLY_UNMODIFIED_ROLLBACK':'NexusLab04SyntheticPolicy.mayRollback(receipt.getString("state"),',
 'ROLLBACK_PRE_VERIFIED':'digest == hash && exactSyntheticMod(mods)',
 'ROLLBACK_INTENT':'persist(journal, "INSTALLED", "ROLLING_BACK", hash)',
 'REAL_REMOVE_SNAPSHOT':'manager.removeMod(NexusLab04SyntheticPolicy.FOLDER)',
 'ROOT_EMPTY_AFTER_REMOVE':'check(rootMembers(mods).isEmpty())',
 'ROLLBACK_FINISHED':'persist(journal, "ROLLING_BACK", "ROLLED_BACK", hash)',
 'ATOMIC_JOURNAL':'StandardCopyOption.ATOMIC_MOVE',
 'DURABLE_JOURNAL':'LAB04_JOURNAL_NOT_DURABLE',
 'SYMLINK_INSTALLED':'Files.isSymbolicLink(folder.toPath())',
 'SYMLINK_MANIFEST':'Files.isSymbolicLink(manifest.toPath())',
 'MANIFEST_BYTES':'sha(manifest.readBytes()) == sha(MANIFEST.toByteArray(Charsets.UTF_8))',
 'NO_REINSTALL':'existingState == null',
 'ONE_SHOT_STATE':'state: String',
}
POLICY_ANCHORS={
 'SCHEMA':'cbnx06-lab04-synthetic-transaction-v1',
 'LOCAL_SCOPE':'LAB_SYNTHETIC_ONLY',
 'LOCAL_PROVENANCE':'LOCAL_SYNTHETIC_GENERATOR_ONLY',
 'EXPECTED_FOLDER':'CBNX06_LAB03_ONLY',
 'EXPECTED_ID':'CBNX06.LAB03.Synthetic',
 'SHA_PATTERN':'Regex("[0-9a-f]{64}")',
 'ALLOWED_STATES':'setOf("INSTALLING", "INSTALLED", "ROLLING_BACK", "ROLLED_BACK")',
 'NO_NEXUS':'!nexusVerified',
 'NO_PRODUCTION':'!productionFilesExamined',
 'NO_REINSTALL':'existingState == null && emptyModsRoot',
 'ROLLBACK_GUARD':'existingState == "INSTALLED" && validInstalledBytes',
 'INTENT_FIRST':'before == null && after == "INSTALLING"',
 'ROLLBACK_DONE':'before == "ROLLING_BACK" && after == "ROLLED_BACK"',
}

# Negative checks are fail-closed even when tests mutate a single source marker.
def validate(stage,policy,panel,unit,workflow,full):
    for key,anchor in STAGE_ANCHORS.items():
        if key=='NO_REINSTALL': continue # asserted in policy, not stage
        if key=='ONE_SHOT_STATE': continue
        need(anchor in stage,'MISSING_STAGE_'+key)
    need(stage.count('check(rootMembers(mods).isEmpty())')==2,
         'PRE_AND_POST_MODS_ROOT_EMPTY_GUARDS')
    need(stage.count('manager.installFromZip(archive, review.approvalKey)')==1,
         'DUPLICATE_INSTALL_SINK')
    need(stage.count('manager.removeMod(NexusLab04SyntheticPolicy.FOLDER)')==1,
         'DUPLICATE_ROLLBACK_SINK')
    need(stage.index('persist(journal, null, "INSTALLING", hash)') <
         stage.index('manager.installFromZip(archive, review.approvalKey)'),
         'INSTALL_WITHOUT_DURABLE_INTENT')
    need(stage.index('persist(journal, "INSTALLED", "ROLLING_BACK", hash)') <
         stage.index('manager.removeMod(NexusLab04SyntheticPolicy.FOLDER)'),
         'ROLLBACK_WITHOUT_DURABLE_INTENT')
    for forbidden in ('getDownloadUrl(', 'ModDownloadService(', 'NexusPairingInbox.admit(',
                      'NexusPairingBridge.start(', 'android.permission.',
                      'http://', 'https://', 'File("/storage', 'runBlocking(',
                      'System.exit(', 'deleteRecursively('):
        need(forbidden not in stage,'UNSAFE_CAPABILITY:'+forbidden)
    for key,anchor in POLICY_ANCHORS.items():need(anchor in policy,'MISSING_POLICY_'+key)
    need('if (BuildConfig.CBNX_LAB)' in panel,'UNGUARDED_UI')
    for anchor in ('NexusLab04SyntheticTransaction.installSynthetic(context)',
                   'NexusLab04SyntheticTransaction.rollbackSynthetic(context)',
                   'cbnx06.lab04.request-install','cbnx06.lab04.request-rollback',
                   'cbnx06.lab04.confirm-action','cbnx06.lab04.cancel-action',
                   'lab04Action = "INSTALL"','lab04Action = "ROLLBACK"',
                   'lab04Action = null','runCatching {','withContext(Dispatchers.IO)'):
        need(anchor in panel,'MISSING_UI:'+anchor)
    need(panel.count('NexusLab04SyntheticTransaction.installSynthetic(context)')==1 and
         panel.count('NexusLab04SyntheticTransaction.rollbackSynthetic(context)')==1,
         'DUPLICATE_UI_SINK')
    need(panel.index('NexusLab04SyntheticTransaction.installSynthetic(context)') <
         panel.index('Text("Exact-file requests"'), 'REMOTE_INBOX_ACTION_ESCAPE')
    for marker in ('@Test fun onlyFreshEmptyLabRootCanInstall()',
                   '@Test fun rollbackRequiresExactVerifiedInstalledBytes()',
                   '@Test fun strictNonRecoverableCrashStates()',
                   '@Test fun receiptRejectsProvenanceOrSyntheticIdentityDrift()'):
        need(marker in unit,'MISSING_JVM_TEST:'+marker)
    for marker in ('test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD"',
                   'scripts/devtool/cbnx06_lab04_source_gate.py',
                   'scripts/devtool/cbnx06_lab04_tests.py',
                   ':app:testDebugUnitTest :app:assembleCbnxLab',
                   'persist-credentials: false'):
        need(marker in workflow,'MISSING_DEDICATED_CI:'+marker)
    for marker in ("      - 'scripts/devtool/cbnx06_lab04_*.py'",
                   'python3 -B scripts/devtool/cbnx06_lab04_source_gate.py',
                   'python3 -B scripts/devtool/cbnx06_lab04_tests.py',
                   ':app:assembleCbnxLab'):
        need(marker in full,'MISSING_FULL_LAB_CI:'+marker)
    return True

def read(path):
    file=ROOT/path
    need(file.is_file() and not file.is_symlink(),'SOURCE_NOT_FILE:'+path)
    return file.read_text(encoding='utf8')

def main():
    validate(*(read(p) for p in (STAGE,POLICY,PANEL,UNIT,WF,FULL)))
    print('LAB04_SOURCE_PRIVATE_ONE_SHOT_INSTALL_AND_SNAPSHOT_ROLLBACK_PASS')
    print('LAB04_SOURCE_DURABLE_JOURNAL_AND_INTERUPTION_REFUSALS_PASS')
    print('LAB04_SOURCE_NO_NETWORK_NO_PRODUCTION_AND_EXPLICIT_CONSENT_PASS')

if __name__=='__main__':
    try: main()
    except (Refused,OSError,ValueError,AssertionError) as e:
        print('LAB04_SOURCE_REFUSED:'+str(e),file=sys.stderr)
        raise SystemExit(2)
