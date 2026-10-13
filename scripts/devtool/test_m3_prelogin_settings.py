"""M3D source navigation boundary checks (run in normal GitHub/Devtool CI)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / 'app/src/main/java/com/sdvsync/MainActivity.kt'
LOGIN = ROOT / 'app/src/main/java/com/sdvsync/ui/screens/LoginScreen.kt'
SETTINGS = ROOT / 'app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt'


class PreLoginSettingsContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = MAIN.read_text()
        cls.login = LOGIN.read_text()
        cls.settings = SETTINGS.read_text()

    def test_route_has_bounded_settings_and_return(self):
        self.assertEqual(self.main.count('composable("prelogin_settings")'), 1)
        route = self.main.split('composable("prelogin_settings")', 1)[1].split('// Main section with bottom bar', 1)[0]
        self.assertIn('preLogin = true', route)
        self.assertIn('onBack = { navController.popBackStack() }', route)
        self.assertIn('onLogout = { navController.popBackStack() }', route)

    def test_steam_success_flow_unchanged(self):
        self.assertIn('startDestination = "login"', self.main)
        self.assertIn('navController.navigate("main")', self.main)
        self.assertIn('popUpTo("login") { inclusive = true }', self.main)
        self.assertIn('is AuthState.LoggedIn', self.login)
        self.assertIn('onLoginSuccess()', self.login)

    def test_settings_button_is_available_before_steam_login(self):
        self.assertIn('onOpenSettings = { navController.navigate("prelogin_settings") }', self.main)
        self.assertIn('if (authState !is AuthState.LoggedIn) {', self.login)
        self.assertIn('onClick = onOpenSettings', self.login)
        self.assertIn('stringResource(R.string.settings_title)', self.login)

    def test_local_file_access_remains_available(self):
        self.assertIn('ShizukuStatusSection(', self.settings)
        self.assertIn('AllFilesAccessSection(', self.settings)
        self.assertIn('SAFAccessSection(', self.settings)
        self.assertIn('onRequestPermission = { viewModel.requestShizukuPermission() }', self.settings)

    def test_steam_only_settings_are_hidden_before_login(self):
        self.assertEqual(self.settings.count('if (!preLogin && state.isLoggedIn) {'), 2)
        self.assertIn('// Auto-sync\n            if (!preLogin && state.isLoggedIn) {', self.settings)
        self.assertIn('// Account\n            if (!preLogin && state.isLoggedIn) {', self.settings)

    def test_no_insecure_auth_override(self):
        self.assertNotIn('AuthState.LoggedIn(', self.main)
        self.assertNotIn('AuthState.LoggedIn(', self.login)
        self.assertNotIn('authenticator.login(', self.main)


if __name__ == '__main__':
    unittest.main()
