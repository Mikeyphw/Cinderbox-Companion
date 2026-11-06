"""Host regression tests for the approved fixed-dark UI-D01 contract."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from earthy_ui_source import contrast, verify


class SingleDarkUiHostTests(unittest.TestCase):
    def test_effective_single_dark_theme_and_denial(self):
        result = verify()
        self.assertEqual(result['overall'], 'PASS_HOST_STATIC', result['checks'])
        self.assertTrue(result['checks']['game_update_fail_closed'])
        self.assertTrue(result['checks']['release_and_device_qualification_disabled'])
        self.assertTrue(result['checks']['no_legacy_theme_selection'])

    def test_known_contrast_ratio(self):
        self.assertAlmostEqual(contrast('#000000', '#FFFFFF'), 21, places=2)

    def test_low_contrast_is_not_greenlit(self):
        self.assertLess(contrast('#F5A0C0', '#FFF3E0'), 4.5)

    def test_frozen_dark_palette_has_readable_pairings(self):
        result = verify()
        self.assertEqual(len(result['contrast_ratios']), 5)
        for name, ratio in result['contrast_ratios'].items():
            with self.subTest(name=name):
                self.assertGreaterEqual(ratio, 4.5)

    def test_legacy_saved_mode_data_is_not_applied(self):
        root = Path(__file__).resolve().parents[2]
        activity = (root/'app/src/main/java/com/sdvsync/MainActivity.kt').read_text()
        settings = (root/'app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt').read_text()
        pref = (root/'app/src/main/java/com/sdvsync/ui/theme/AppearancePreferences.kt').read_text()
        self.assertIn('ReplaceFileCorruptionHandler', pref)
        self.assertIn('SdvSyncTheme {', activity)
        self.assertNotIn('appearance.mode.resolve(', activity)
        self.assertNotIn('appearanceStore.setStyle(', settings)
        self.assertNotIn('appearanceStore.setMode(', settings)
        self.assertIn('Dark · default', settings)


if __name__ == '__main__':
    unittest.main()
