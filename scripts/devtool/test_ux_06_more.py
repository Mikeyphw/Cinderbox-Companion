"""UX-06 source gate negative-contract checks (host only)."""
import unittest
from unittest.mock import patch
import ux_06_more_gate as gate

class ApprovedMoreContract(unittest.TestCase):
    def test_required_source_and_safety(self):
        self.assertFalse(gate.check()['release_enabled'])
    def test_unknown_source_cannot_count_as_pass(self):
        with patch.object(gate, 'source', side_effect=AssertionError('missing')):
            with self.assertRaises(AssertionError): gate.check()
    def test_no_implicit_access_operations(self):
        src=gate.source('app/src/main/java/com/sdvsync/ui/screens/ApprovedMoreScreen.kt')
        for op in ('setFileAccessMode(', 'requestShizukuPermission(',
                   'toggleAutoSync(', 'startDownload(', 'deleteRecursively('):
            with self.subTest(op=op): self.assertNotIn(op, src)
    def test_legacy_secondary_route_kept(self):
        source=gate.source('app/src/main/java/com/sdvsync/MainActivity.kt')
        self.assertIn('composable("more_advanced")',source)
        self.assertIn('composable("prelogin_settings")',source)

if __name__=='__main__': unittest.main()
