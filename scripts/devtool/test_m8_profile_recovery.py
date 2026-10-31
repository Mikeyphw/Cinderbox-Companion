"""M8 source contracts. Kotlin unit tests cover process-death filesystem recovery."""
import unittest
from pathlib import Path
from ci_workflow_contract import effective_ci_source
ROOT=Path(__file__).resolve().parents[2]
def read(name):return effective_ci_source(ROOT,name)

class M8ProfileSafety(unittest.TestCase):
 def test_journal_precedes_renames_and_recovery_is_reverse(self):
  source=read("app/src/main/java/com/sdvsync/mods/ModProfileTransaction.kt")
  self.assertLess(source.index('prepare(moves)\n        try {'),source.index('check(source.renameTo(target))'))
  for anchor in ('stream.fd.sync()', 'moves.indices.reversed()',
                 'if (f == t', 'target.renameTo(source)', 'journal.delete()',
                 'LinkOption.NOFOLLOW_LINKS', 'Files.isSymbolicLink(child.toPath())'):
   self.assertIn(anchor,source)
  self.assertNotIn('deleteRecursively(',source)
 def test_all_mod_operations_recover_pending_profile(self):
  src=read('app/src/main/java/com/sdvsync/mods/ModFileManager.kt')
  for signature in ('restoreSnapshot(id: String)', 'previewFromZip(zipFile: File)',
                    'listInstalledMods(): List<InstalledMod>', 'applyProfileSafely(profile: ModProfile',
                    'enableMod(folderName: String)', 'disableMod(folderName: String)',
                    'removeMod(folderName: String)'):
   block=src.split(signature,1)[1].split('\n    }',1)[0]
   self.assertIn('profileTransactions.recover()',block,signature)
  self.assertIn('return profileTransactions.apply(preview.steps.map {',src)
  self.assertIn('preview.fingerprint == expectedFingerprint',src)
  self.assertIn('preview.blockers.isEmpty()',src)
 def test_android_tests_cover_crashes_and_ambiguity(self):
  tests=read('app/src/test/java/com/sdvsync/mods/ModProfileTransactionTest.kt')
  for name in ('journalBeforeAnyRenameRollsBackAndClears',
               'deathBetweenTwoRenamesRollsBackExactly',
               'deathAfterAllRenamesStillRollsBack',
               'collisionPreservesAllFoldersAndKeepsJournal',
               'unsafeOrConflictingPlansRejectWithoutJournal',
               'symlinkAfterCrashIsFailClosed'):
   self.assertIn(name,tests)
 def test_registered_both_workflows(self):
  for name in ('.github/workflows/build.yml','.github/workflows/devtool-android-build.yml'):
   self.assertIn('test_m8_*.py',read(name))
 def test_m7_contract_strengthened_not_skipped(self):
  old=read('scripts/devtool/test_m7_mod_compatibility.py')
  self.assertIn('profileTransactions.apply(',old)
  self.assertIn('target.renameTo(source)',old)
  self.assertIn('preview.blockers.isEmpty()',old)
if __name__=='__main__':unittest.main()
