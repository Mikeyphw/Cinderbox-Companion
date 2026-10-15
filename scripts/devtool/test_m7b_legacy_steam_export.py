"""Regression against inadvertently replacing M3G export when adding M7B bug reporting."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]

class M7BLegacySteamExport(unittest.TestCase):
    def test_both_separate_saf_exports_are_available(self):
        src=(ROOT/'app/src/main/java/com/sdvsync/ui/screens/SteamDiagnosticsScreen.kt').read_text('utf-8')
        self.assertIn('SteamDiagnostics.exportJson()',src)
        self.assertIn('SanitizedBugReport.exportJson()',src)
        self.assertIn('steamExport.launch("cinderbox-steam-diagnostics.json")',src)
        self.assertIn('export.launch("cinderbox-sanitized-bug-report.json")',src)
        self.assertEqual(src.count('CreateDocument("application/json")'),2)
        self.assertIn('Export Steam connection history',src)
        self.assertIn('Export sanitized bug report',src)
        self.assertEqual(src.count('SteamDiagnostics.exportJson()'),1)
        self.assertEqual(src.count('SanitizedBugReport.exportJson()'),1)

if __name__=='__main__': unittest.main()
