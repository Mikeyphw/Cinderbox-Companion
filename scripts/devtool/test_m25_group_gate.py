import unittest
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[2]
def read(p):return (ROOT/p).read_text(encoding='utf-8')
class M25GroupR1SourceTests(unittest.TestCase):
    def test_selection_is_cleared_on_visibility_change(self):
        s=read('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
        for mark in ('fun setFilter(', 'fun setGroupMode(', 'fun setSearchQuery(',
                     'selectedModIds = emptySet()', 'bulkPreview = null',
                     'state.selectedModIds.intersect(visibleIds)'):
            self.assertIn(mark,s)
    def test_bulk_preview_has_no_apply_or_fs_mutation(self):
        core=read('app/src/main/java/com/sdvsync/mods/ModSelectionPolicy.kt')
        for forbidden in ('java.io.File','renameTo','deleteRecursively','applyProfileSafely',
                          'enableMod(', 'disableMod(', 'NexusClientCollections'):
            self.assertNotIn(forbidden,core)
    def test_selection_has_visible_explicit_count_and_no_background_toggle(self):
        ui=read('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt')
        self.assertIn('state.selectedModIds.size',ui)
        self.assertIn('if (state.selectionMode)',ui)
        self.assertIn('No folders were changed',ui)
    def test_r43_recovery_and_release_constraints_unchanged(self):
        core=read('app/src/main/java/com/sdvsync/mods/ModSelectionPolicy.kt')
        self.assertIn('ModCompatibility.preview(',core)
        self.assertNotIn('ModProfileTransaction(',core)
