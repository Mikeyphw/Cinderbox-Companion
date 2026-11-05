import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def text(path):return (ROOT/path).read_text(encoding='utf-8')
class M25UpdateTests(unittest.TestCase):
    def test_update_errors_retain_prior_cache(self):
        checker=text('app/src/main/java/com/sdvsync/mods/api/SmapiUpdateChecker.kt')
        self.assertIn('throw IllegalStateException("SMAPI update lookup unavailable", e)',checker)
        vm=text('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
        self.assertIn('previous results retained',vm)
        self.assertIn('dataStore.setUpdateSnapshot(result)',vm)
    def test_no_install_mutation_from_update_policy(self):
        core=text('app/src/main/java/com/sdvsync/mods/ModUpdatePolicy.kt')
        for forbidden in ('installFromZip(', 'applyProfileSafely(', 'File(', 'deleteRecursively(',
                          'NexusClientCollections', 'getNexusApiKey'):
            self.assertNotIn(forbidden, core)
    def test_ignored_update_writes_are_atomic(self):
        data=text('app/src/main/java/com/sdvsync/mods/ModDataStore.kt')
        block=data.split('suspend fun setIgnoredUpdateVersion(')[1].split('private fun parseIgnoredUpdates(')[0]
        self.assertIn('context.modDataStore.edit',block)
        self.assertIn('ModUpdatePolicy.checkedCandidateVersion',block)
    def test_ui_makes_ignored_visible_and_reversible(self):
        ui=text('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt')
        for mark in ('toggleIgnoredUpdates()', 'unignoreUpdate(update.uniqueID)',
                     'ignoreUpdate(update.uniqueID)', 'Show ignored updates'):
            self.assertIn(mark,ui)
    def test_unsupported_remote_version_not_auto_upgrade(self):
        k=text('app/src/main/java/com/sdvsync/mods/ModUpdatePolicy.kt')
        self.assertIn('UNCOMPARABLE',k)
        self.assertIn('UpdateAssessment.NEWER &&',k)
