"""M10 offline source checks. Android Kotlin/JVM tests run separately in CI."""
from pathlib import Path
import unittest
from ci_workflow_contract import effective_ci_source
ROOT = Path(__file__).resolve().parents[2]
def read(path): return effective_ci_source(ROOT,path)
class M10Contracts(unittest.TestCase):
    def test_only_preverified_source_can_repair(self):
        s=read('app/src/main/java/com/sdvsync/download/VerifiedGameRepair.kt')
        self.assertIn('GameFileIntegrity(privateRoot).verifyRecorded(it).passed',s)
        self.assertIn('GameDownloadRecovery(privateRoot).pending() != null',s)
        self.assertIn('check(verifiedSource(source))',s)
        self.assertIn('check(!hasPendingDownload())',s)
        self.assertIn('check(source != dest',s)
    def test_stale_approval_and_transaction_recovery(self):
        s=read('app/src/main/java/com/sdvsync/download/VerifiedGameRepair.kt')
        for marker in ('live.fingerprint == review.fingerprint','writeJournal(dest, stage, plans)',
                'check(recover())','fun recover(): Boolean','if (actual != plan.previous && actual != plan.wanted) return false',
                'atomicReplace(', 'if (plan.previous.isEmpty())', 'backupRoot'):
            self.assertIn(marker,s)
    def test_no_unreviewed_target_mutation(self):
        s=read('app/src/main/java/com/sdvsync/download/VerifiedGameRepair.kt')
        preview=s.split('fun preview(sourceDir:',1)[1].split('private data class Recovery(',1)[0]
        for marker in ('atomicReplace(', 'target.delete()', 'writeJournal('):
            self.assertNotIn(marker,preview)
        self.assertIn('items.map { GameRepairChange',preview)
    def test_ui_requires_explicit_review(self):
        ui=read('app/src/main/java/com/sdvsync/ui/screens/InstallationHealthScreen.kt')
        for mark in ('Preview verified repair','Review selective game repair',
                     'Approve repair','repairEngine.preview(', 'repairEngine.apply(preview)',
                     'repairEngine.recover()', 'items(preview.changes)'):
            self.assertIn(mark,ui)
    def test_unit_tests_and_both_ci_workflows(self):
        tests=read('app/src/test/java/com/sdvsync/download/VerifiedGameRepairTest.kt')
        for mark in ('processDeathBetweenWritesRollsBack','externalEditsAfterCrashBlockAllRollback',
                'repairsOnlyDiffsAndPreservesTargetExtras', 'unverifiedSourceCannotProducePreview'):
            self.assertIn(mark,tests)
        for file in ('.github/workflows/build.yml','.github/workflows/devtool-android-build.yml'):
            self.assertIn('test_m10_*.py',read(file))
if __name__=='__main__': unittest.main()
