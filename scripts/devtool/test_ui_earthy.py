"""Host checks for Earthy color pairs, appearance safety and source policy."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from earthy_ui_source import contrast, verify


class EarthyUiHostTests(unittest.TestCase):
    def test_palette_and_source_contract(self):
        result = verify()
        self.assertEqual(result['overall'], 'PASS_HOST_STATIC', result['checks'])

    def test_known_contrast_ratio(self):
        self.assertAlmostEqual(contrast('#000000', '#FFFFFF'), 21, places=2)

    def test_low_contrast_is_not_greenlit(self):
        self.assertLess(contrast('#F5A0C0', '#FFF3E0'), 4.5)

    def test_both_theme_modes_and_fallback_paths(self):
        root = Path(__file__).resolve().parents[2]
        code = (root/'app/src/main/java/com/sdvsync/ui/theme/AppearancePreferences.kt').read_text()
        for source in ['AppearanceStyle.entries.firstOrNull', 'AppearanceMode.entries.firstOrNull', 'SYSTEM -> systemDark', 'LIGHT -> false', 'DARK -> true']:
            self.assertIn(source, code)


if __name__ == '__main__':
    unittest.main()
