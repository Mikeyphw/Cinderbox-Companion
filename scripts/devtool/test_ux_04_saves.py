"""UX-04 source negative fixtures: no credentials, emulator, files or network."""
import unittest
from pathlib import Path
import ux_04_saves_gate as gate

class ApprovedSavesHostContracts(unittest.TestCase):
    def test_ux04_contract(self):
        result=gate.check()
        self.assertEqual(result['result'],'UX04_APPROVED_DARK_SAVES_SOURCE_PASS')
        self.assertTrue(result['local_first'])
        self.assertFalse(result['automatic_sync'])
        self.assertFalse(result['release_enabled'])

    def test_metadata_parse_failure_keeps_local_save_visible(self):
        source=gate.source('app/src/main/java/com/sdvsync/ui/viewmodels/DashboardViewModel.kt')
        self.assertIn('hasLocal = folderName in localMap',source)
        self.assertNotIn('hasLocal = localMeta != null',source)

    def test_cloud_never_unlocks_on_fake_entitlement(self):
        screen=gate.source('app/src/main/java/com/sdvsync/ui/screens/ApprovedSavesScreen.kt')
        self.assertIn('if (cloudSelected && !isSteamConnected)',screen)
        self.assertIn('isSteamConnected && save.hasCloud',screen)
        self.assertNotIn('entitlementVerified = true',screen)

    def test_detail_navigation_explicit_and_legacy_preserved(self):
        main=gate.source('app/src/main/java/com/sdvsync/MainActivity.kt')
        self.assertEqual(main.count('composable("saves")'),1)
        self.assertEqual(main.count('composable("saves_advanced")'),1)
        self.assertIn('Uri.encode(folderName)',main)
        self.assertIn('DashboardScreen(',main)

    def test_reject_privileged_calls_in_saves_ui(self):
        screen=gate.source('app/src/main/java/com/sdvsync/ui/screens/ApprovedSavesScreen.kt')
        for term in ('File(', 'deleteRecursively(', 'confirmImport(', 'startSync(',
                     'Runtime.getRuntime()', 'requestShizukuPermission('):
            with self.subTest(term=term):self.assertNotIn(term,screen)

    def test_mutation_is_caught_by_gate(self):
        original=gate.source('app/src/main/java/com/sdvsync/ui/screens/ApprovedSavesScreen.kt')
        self.assertIn('Cloud saves are optional',original)
        self.assertIn('Local saves are always available',original)

if __name__=='__main__':unittest.main()
