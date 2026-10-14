"""Source regressions for M5. Independent of Gradle; CI also runs JVM tests."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]

def read(p):return (ROOT/p).read_text(encoding='utf-8')

class M5SafeOperationsTest(unittest.TestCase):
    def test_import_requires_preview(self):
        m=read('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
        self.assertIn('pending.enqueue(temp,',m)
        self.assertIn('fun confirmPendingReview()',m)
        self.assertIn('fileManager.installFromZip(archive, prior.approvalKey)',m)
        self.assertIn('fun discardPendingReview()',m)
        self.assertNotIn('fileManager.installFromZip(tempFile)',m)
    def test_remote_download_does_not_install(self):
        service=read('app/src/main/java/com/sdvsync/mods/ModDownloadService.kt')
        self.assertIn('ModReviewQueue(filesDir).enqueue(',service)
        self.assertNotIn('fileManager.installFromZip(',service)
        self.assertIn('ModDownloadState.REVIEW_REQUIRED',service)
    def test_fail_closed_legacy_mod_install(self):
        src=read('app/src/main/java/com/sdvsync/mods/ModFileManager.kt')
        self.assertIn('fun installFromZip(zipFile: File): InstallResult = InstallResult.Error',src)
        self.assertIn('currentReview.approvalKey == approvedReviewKey',src)
        self.assertIn('safety.snapshot(targetDir)',src)
        self.assertIn('safety.begin(targetDir.name, snapshot, "install")',src)
    def test_mod_removal_is_snapshot_backed(self):
        src=read('app/src/main/java/com/sdvsync/mods/ModFileManager.kt')
        self.assertIn('safety.snapshot(folder)',src)
        self.assertIn('safety.begin(folderName, snapshot, "remove")',src)
        self.assertIn('fun restoreSnapshot(id: String)',src)
    def test_visible_review_and_restore_controls(self):
        ui=read('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt')
        self.assertIn('Approve install',ui)
        self.assertIn('Discard archive',ui)
        self.assertIn('Retained mod snapshots',ui)
        self.assertIn('Restore mod snapshot?',ui)
    def test_operations_and_journal_are_app_private(self):
        safety=read('app/src/main/java/com/sdvsync/mods/ModSafety.kt')
        self.assertIn('mod-operation.properties',safety)
        self.assertIn('mod-snapshots',safety)
        self.assertIn('private val modsDir: File',safety)
        self.assertIn('fun recover(): Boolean',safety)
    def test_ci_enforces_m5(self):
        for p in ('.github/workflows/build.yml','.github/workflows/devtool-android-build.yml'):
            self.assertIn("test_m5_*.py",read(p))

if __name__=='__main__':unittest.main()
