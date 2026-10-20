"""M11 source regression: true unknown-size semantics, save preservation and CI wiring."""
from pathlib import Path
import unittest
from ci_workflow_contract import effective_ci_source
ROOT=Path(__file__).resolve().parents[2]
def src(path): return effective_ci_source(ROOT,path)

class M11Contracts(unittest.TestCase):
    def test_copy_budget_guard_and_download_without_user_size_guess(self):
        planner=src('app/src/main/java/com/sdvsync/local/StoragePlanner.kt')
        vm=src('app/src/main/java/com/sdvsync/ui/viewmodels/GameDownloadViewModel.kt')
        manager=src('app/src/main/java/com/sdvsync/download/GameDownloadManager.kt')
        self.assertIn('payloadBytes == null',planner)
        self.assertIn('availableBytes',planner)
        self.assertIn('DEFAULT_RESERVE',planner)
        self.assertIn('StoragePreflight.check(File(current.installDirectory))',vm)
        self.assertNotIn('StoragePlanner.downloadPlan(',vm)
        self.assertNotIn('Storage budget',src('app/src/main/java/com/sdvsync/ui/screens/GameDownloadScreen.kt'))
        self.assertIn('StoragePlanner.copyPlan(destDir, filesToCopy.map { it.first })',manager)
        self.assertIn('if (copyBudget.sufficient != true)',manager)

    def test_removed_manual_download_storage_budget(self):
        ui=src('app/src/main/java/com/sdvsync/ui/screens/GameDownloadScreen.kt')
        self.assertNotIn('Estimated game download size',ui)
        self.assertNotIn('Storage budget',ui)
        self.assertIn('Choose folder with Android',ui)

    def test_direct_restore_never_deletes_original_before_staging(self):
        tx=src('app/src/main/java/com/sdvsync/saves/SaveRestoreTransaction.kt')
        backups=src('app/src/main/java/com/sdvsync/saves/SaveBackupManager.kt')
        self.assertIn('m11-save-restore.properties',tx)
        self.assertIn('if (hadTarget) check(destination.renameTo(hold))',tx)
        self.assertIn('check(stage.renameTo(destination))',tx)
        self.assertIn('if (journaled) check(recover())',tx)
        self.assertIn('StoragePlanner.plan(parent, Math.addExact(originalBytes, sourceBytes))',tx)
        self.assertIn('createBackupDirectory(targetDir.name)',backups)
        self.assertIn('restoreTransaction.restore(source, targetDir)',backups)
        self.assertNotIn('targetDir.listFiles()?.forEach { it.delete() }',backups)

    def test_privileged_restore_verifies_and_compensates(self):
        view=src('app/src/main/java/com/sdvsync/ui/viewmodels/BackupListViewModel.kt')
        self.assertIn('backupManager.backupSaveData(saveFolderName, currentFiles)',view)
        self.assertIn('readBack[name]?.contentEquals(data) == true',view)
        self.assertIn('saveFileManager.writeLocalSave(saveFolderName, currentFiles)',view)
        self.assertIn('Manual recovery required',view)
        self.assertIn('backupManager.listBackups(saveFolderName)',view)

    def test_ci_enforces_m11(self):
        for name in ('.github/workflows/build.yml','.github/workflows/devtool-android-build.yml'):
            self.assertIn("test_m11_*.py",src(name))

if __name__=='__main__':unittest.main()
