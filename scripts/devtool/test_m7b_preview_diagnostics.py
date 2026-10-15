"""Source safety regressions for M7B; full Android Gradle/JVM tests run in CI."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[2]
def read(path): return (ROOT / path).read_text(encoding="utf-8")
class M7BSafety(unittest.TestCase):
    def test_preview_is_read_only_and_approval_rechecks_staleness(self):
        engine = read("app/src/main/java/com/sdvsync/sync/SyncEngine.kt")
        preview = engine.split("suspend fun previewChanges(",1)[1].split("suspend fun executeReviewedSync(",1)[0]
        self.assertIn("listCloudSaves()",preview)
        self.assertIn("readLocalSave",preview)
        for word in ("uploadSave(","writeLocalSave(","backupSaveData("):
            self.assertNotIn(word,preview)
        execute = engine.split("suspend fun executeReviewedSync(",1)[1].split("private fun categorizeException(",1)[0]
        self.assertIn("live.fingerprint != preview.fingerprint",execute)
        self.assertIn("SyncResult.Error",execute)
    def test_manual_ui_routes_all_force_and_normal_to_preview(self):
        screen=read("app/src/main/java/com/sdvsync/ui/screens/SyncDetailScreen.kt")
        self.assertIn("viewModel.requestSyncPreview(saveFolderName, SyncPreviewDirection.PULL",screen)
        self.assertIn("viewModel.requestSyncPreview(saveFolderName, SyncPreviewDirection.PUSH",screen)
        self.assertNotIn("viewModel.pullSave(saveFolderName",screen)
        self.assertNotIn("viewModel.pushSave(saveFolderName",screen)
        self.assertIn("viewModel.approveSyncPreview()",screen)
        vm=read("app/src/main/java/com/sdvsync/ui/viewmodels/SyncDetailViewModel.kt")
        self.assertIn("engine.executeReviewedSync(approvedPreview, progress)",vm)
        self.assertIn("SyncOperationDiagnostics.record",vm)
    def test_export_has_only_allowlisted_fields(self):
        report=read("app/src/main/java/com/sdvsync/diagnostics/SanitizedBugReport.kt")
        self.assertIn("app_version", report)
        self.assertIn("android_api", report)
        self.assertIn("sync_operations",report)
        for forbidden in ("AppLogger.getLogFiles", "stackTrace", "farmerName", "SteamSessionStore"):
            self.assertNotIn(forbidden,report)
        ledger=read("app/src/main/java/com/sdvsync/diagnostics/SyncOperationDiagnostics.kt")
        self.assertIn("MAX_EVENTS = 48",ledger)
        self.assertIn("allowedErrors",ledger)
        self.assertIn('else "UNKNOWN"', ledger)
    def test_kotlin_unit_tests_and_ci_registration(self):
        tests=read("app/src/test/java/com/sdvsync/sync/SyncChangePreviewTest.kt")
        for name in ("previewListsActualWritesWithoutProposingDeletes", "aChangedLocalByteOrCloudStampInvalidatesPreview", "diagnosticCodesAreCategoricalNotRawExceptionText"):
            self.assertIn(name,tests)
        for workflow in (".github/workflows/build.yml", ".github/workflows/devtool-android-build.yml"):
            self.assertIn("test_m7b_*.py",read(workflow))
if __name__=="__main__":unittest.main()
