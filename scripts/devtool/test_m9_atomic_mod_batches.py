"""M9 source contracts. JVM tests separately exercise actual staged filesystem transitions."""
from pathlib import Path
import unittest
from ci_workflow_contract import effective_ci_source
R=Path(__file__).resolve().parents[2]
def read(path):return effective_ci_source(R,path)
class M9BatchContracts(unittest.TestCase):
 def test_all_archive_mods_commit_as_one_transaction(self):
  s=read('app/src/main/java/com/sdvsync/mods/ModFileManager.kt')
  self.assertIn('batchTransactions.install(entries, snapshot =',s)
  self.assertIn('safety.snapshot(target)',s)
  self.assertNotIn('safety.begin(targetDir.name, snapshot, "install")',s)
  self.assertIn('currentReview.approvalKey == approvedReviewKey',s)
  self.assertIn('entries.map { it.targetName } == currentReview.changes.map { it.folder }',s)
 def test_crash_recovery_precedes_all_mod_mutations(self):
  s=read('app/src/main/java/com/sdvsync/mods/ModFileManager.kt')
  for name in ('restoreSnapshot','previewFromZip','listInstalledMods','applyProfileSafely',
               'enableMod','disableMod','removeMod'):
   seg=s.split('fun '+name+'(',1)[1].split('\n    }',1)[0]
   self.assertIn('batchTransactions.recover()',seg,name)
 def test_atomic_recovery_fail_closed_and_bound_to_bytes(self):
  t=read('app/src/main/java/com/sdvsync/mods/ModBatchTransaction.kt')
  for token in ('m9-mod-batch.properties','FileOutputStream(temp)', 'stream.fd.sync()',
                'if (journalPublished)', 'fun recover(): Boolean', 'state(plan, it)',
                'treeHash(target)', 'treeHash(held)', 'snapshot(existing)',
                'fun destinationFingerprint(', 'State.PUBLISHED', 'State.HELD',
                'State.ADDED', 'Symlink in mod tree'):
   self.assertIn(token,t)
  review=read('app/src/main/java/com/sdvsync/mods/ModSafety.kt')
  self.assertIn('existingDigest',review)
 def test_batch_jvm_tests_and_both_ci_lanes(self):
  s=read('app/src/test/java/com/sdvsync/mods/ModBatchTransactionTest.kt')
  for test in ('successfulBatchCommitsAllWithoutJournal','exceptionDuringSecondModRollsBackAll',
               'processDeathAfterFirstModRecoversAll','collisionAfterDeathBlocksWholeRecovery',
               'editedPublishedModBlocksRecoveryWithoutDeleting','symlinkAfterCrashBlocksRecovery'):
   self.assertIn(test,s)
  for wf in ('.github/workflows/build.yml','.github/workflows/devtool-android-build.yml'):
   self.assertIn('test_m9_*.py',read(wf))
if __name__=='__main__': unittest.main()
