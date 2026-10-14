"""Regression guard: M6's interrupted-download StateFlow must compile with its enum import.

This is a source-level smoke test. GitHub Android Gradle compile remains authoritative.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

class M6ViewModelImportContract(unittest.TestCase):
    def test_game_download_viewmodel_imports_state_used_by_recovery_collector(self):
        src = (ROOT / 'app/src/main/java/com/sdvsync/ui/viewmodels/GameDownloadViewModel.kt').read_text(encoding='utf-8')
        manager = (ROOT / 'app/src/main/java/com/sdvsync/download/GameDownloadManager.kt').read_text(encoding='utf-8')
        self.assertIn('enum class DownloadState {', manager)
        self.assertIn('import com.sdvsync.download.DownloadState\n', src)
        self.assertIn('DownloadState.ERROR, DownloadState.CANCELLED, DownloadState.COMPLETED', src)
        self.assertIn('downloadManager.pendingDownload()', src)

if __name__ == '__main__':
    unittest.main()
