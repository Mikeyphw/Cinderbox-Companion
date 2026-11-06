"""UX-03 hosted source/negative tests; no device, Steam access or files mutations."""
from pathlib import Path
import tempfile
import unittest
import ux_03_game_gate as gate

class GameUxContract(unittest.TestCase):
    def test_real_source_contract(self):
        result=gate.check()
        self.assertTrue(result['no_write_authorization'])
        self.assertFalse(result['release_enabled'])
        self.assertFalse(result['native_screenshot_parity_verified'])

    def test_game_has_no_privileged_operations(self):
        text=gate.source('app/src/main/java/com/sdvsync/ui/screens/ApprovedGameScreen.kt')
        for action in ('startDownload(', 'deleteRecursively(', 'File(', 'installPackage('):
            with self.subTest(action=action):self.assertNotIn(action,text)

    def test_connection_does_not_grant_entitlement(self):
        text=gate.source('app/src/main/java/com/sdvsync/ui/screens/ApprovedGameScreen.kt')
        self.assertIn('Game entitlement, access and storage still require verification.',text)
        self.assertIn('if (isSteamConnected) onOpenGameSetup else onConnectSteam',text)
        self.assertNotIn('entitlementVerified = true',text)

    def test_route_gates_and_previous_screen_preserved(self):
        main=gate.source('app/src/main/java/com/sdvsync/MainActivity.kt')
        self.assertEqual(main.count('composable("game_download")'),1)
        self.assertEqual(main.count('composable("game_setup_advanced")'),1)
        self.assertIn('GameDownloadScreen(',main)
        self.assertIn('onOpenInstallationHealth = { parentNavController.navigate("installation_health") }',main)

    def test_release_denied_at_service_not_only_ui(self):
        game=gate.source('app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt')
        self.assertIn('const val LIVE_UPDATES_ENABLED: Boolean = false',game)
        self.assertIn('const val DEVICE_ACCEPTED: Boolean = false',game)

if __name__=='__main__':unittest.main()
