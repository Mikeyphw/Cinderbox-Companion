"""M7A source contract tests (no Gradle required); Android JVM tests verify semantics."""
from pathlib import Path
import unittest
from ci_workflow_contract import effective_ci_source
ROOT=Path(__file__).resolve().parents[2]
def read(path):return effective_ci_source(ROOT,path)
class M7ProfileSafetyTest(unittest.TestCase):
 def test_profile_apply_uses_guarded_transaction(self):
  s=read('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
  self.assertIn('fileManager.applyProfileSafely(profile, approvedFingerprint)',s)
  self.assertNotIn('fileManager.enableMod(mod.folderName)',s)
  self.assertNotIn('fileManager.disableMod(mod.folderName)',s)
 def test_source_guard_and_rollback(self):
  s=read('app/src/main/java/com/sdvsync/mods/ModFileManager.kt')
  for term in ('@Synchronized fun applyProfileSafely', 'expectedFingerprint',
               'preview.blockers.isEmpty()', 'Files.isSymbolicLink(from.toPath())',
               'safeFolder(step.fromFolder)', 'profileTransactions.apply(',
               'profileTransactions.recover()'):
   self.assertIn(term,s)
  transaction=read('app/src/main/java/com/sdvsync/mods/ModProfileTransaction.kt')
  for term in ('journal.delete()', 'moves.indices.reversed()',
               'source.renameTo(target)', 'target.renameTo(source)',
               'private fun safe(', 'fun recover(): Boolean'):
   self.assertIn(term,transaction)
 def test_review_and_dependency_audit_visible(self):
  s=read('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt')
  self.assertIn('Mod compatibility audit',s)
  self.assertIn('preview.blockers.isEmpty()',s)
  self.assertIn('viewModel.applyProfile(profile, preview.fingerprint)',s)
  m=read('app/src/main/java/com/sdvsync/mods/ModCompatibility.kt')
  self.assertIn('manifest.dependencies.filter { it.isRequired }',m)
  self.assertIn('manifest.contentPackFor',m)
  self.assertIn('SMAPI version not validated',m)
 def test_stale_dependency_preview_and_serialized_mod_mutations(self):
  compat=read('app/src/main/java/com/sdvsync/mods/ModCompatibility.kt')
  files=read('app/src/main/java/com/sdvsync/mods/ModFileManager.kt')
  self.assertIn('val deps = manifest.dependencies', compat)
  self.assertIn('manifest.contentPackFor?.uniqueID.orEmpty()', compat)
  self.assertIn('@Synchronized fun enableMod',files)
  self.assertIn('@Synchronized fun disableMod',files)
 def test_coverage_registered_in_both_ci_workflows(self):
  for p in ('.github/workflows/build.yml','.github/workflows/devtool-android-build.yml'):
   self.assertIn("test_m7_*.py",read(p))
 def test_junit_semantic_cases(self):
  s=read('app/src/test/java/com/sdvsync/mods/ModCompatibilityTest.kt')
  for term in ('missingRequiredDependencyBlocksProfile','missingOptionalDependencyDoesNotBlock',
               'insufficientVersionBlocksAndEqualVersionPasses','contentPackProviderMustBePresent',
               'duplicateIdAndMissingProfileModBlocked'):
   self.assertIn(term,s)
if __name__=='__main__':unittest.main()
