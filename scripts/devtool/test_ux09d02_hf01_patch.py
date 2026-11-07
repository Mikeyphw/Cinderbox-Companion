#!/usr/bin/env python3
"""Hermetic negative tests for source-pinned single-import repair."""
import sys,pathlib,hashlib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from ux09d02_hf01_patch import transform,PreimageMismatch,BEFORE_SHA256,AFTER_SHA256,PATH

class ImportFixContract(unittest.TestCase):
    def test_expected_path_and_digests(self):
        self.assertEqual(PATH,'app/src/androidTest/java/com/sdvsync/ui/ux/Ux09D02RealRouteEvidenceTest.kt')
        self.assertEqual(len(BEFORE_SHA256),64)
        self.assertEqual(len(AFTER_SHA256),64)
        self.assertNotEqual(BEFORE_SHA256,AFTER_SHA256)
    def test_reject_unexpected_source(self):
        with self.assertRaises(PreimageMismatch): transform(b'import androidx.compose.ui.test.assertDoesNotExist\n')
        with self.assertRaises(PreimageMismatch): transform(b'')
    def test_reject_reapplication_of_patch(self):
        with self.assertRaises(PreimageMismatch): transform(b'import android.content.Context\n')
    def test_no_release_or_production_changes_in_patch(self):
        import inspect,ux09d02_hf01_patch as patch
        code=inspect.getsource(patch)
        self.assertNotIn('app/src/main/',code)
        self.assertNotIn('gradle build',code)
        self.assertIn('BEFORE_BLOB=',code)
        self.assertIn('AFTER_SHA256=',code)

if __name__=='__main__':unittest.main()
