import importlib.util
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('verifyux',ROOT/'scripts/devtool/m24_verify_ux_gate.py')
ux=importlib.util.module_from_spec(spec);spec.loader.exec_module(ux)
class VerificationUxSourceTests(unittest.TestCase):
    def test_source_gate(self):
        self.assertEqual(ux.main(),0)
    def test_file_pass_progress_is_distinct(self):
        integrity=(ROOT/'app/src/main/java/com/sdvsync/download/GameFileIntegrity.kt').read_text()
        self.assertIn('hashing pass 1 of 2',integrity)
        self.assertIn('hashing pass 2 of 2',integrity)
        self.assertIn('phaseProgress',integrity)
    def test_existing_safe_resume_unchanged(self):
        mgr=(ROOT/'app/src/main/java/com/sdvsync/download/GameDownloadManager.kt').read_text()
        for word in ('recovery.beginStaged(', 'recovery.requireMatching(', 'recovery.requireSteamBuildId('):
            self.assertIn(word,mgr)
    def test_no_saf_as_direct_file_shortcut(self):
        pick=(ROOT/'app/src/main/java/com/sdvsync/local/M24AndroidFolderPicker.kt').read_text()
        self.assertIn('com.android.externalstorage.documents',pick)
        self.assertNotIn('uri.path?.let(::File)',pick)
if __name__=='__main__':unittest.main()
