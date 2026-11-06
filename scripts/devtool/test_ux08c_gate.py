"""Source-level and safety regression contracts; real runtime belongs to Actions."""
import unittest
from pathlib import Path
import ux08c_gate

class UX08CSourceTest(unittest.TestCase):
    def test_current_source_gate(self):
        self.assertEqual(ux08c_gate.check()['result'],'UX08C_SAVE_AND_BACKUP_READ_ONLY_SOURCE_PASS')
    def test_overview_does_not_write(self):
        s=ux08c_gate.source('app/src/main/java/com/sdvsync/ui/screens/ApprovedSaveDeepScreen.kt')
        for token in ('restoreBackup(', 'requestSyncPreview(', 'setFileAccessMode(', 'File(', 'Runtime.getRuntime('):
            self.assertNotIn(token,s)
    def test_old_guarded_flows_remain(self):
        m=ux08c_gate.source('app/src/main/java/com/sdvsync/MainActivity.kt')
        for route in ('save_viewer/{saveFolderName}', 'backups/{saveFolderName}',
                      'sync_detail/{saveFolderName}/{hasCloud}/{hasLocal}'):
            self.assertEqual(m.count(route),1)
    def test_conditional_actions(self):
        s=ux08c_gate.source('app/src/main/java/com/sdvsync/ui/screens/ApprovedSaveDeepScreen.kt')
        self.assertIn('if (snapshot.hasLocal)',s)
        self.assertIn('if (snapshot.hasCloud || snapshot.hasLocal)',s)
        self.assertIn('singleOrNull { it.folderName == saveFolderName }',s)

if __name__=='__main__':unittest.main()
