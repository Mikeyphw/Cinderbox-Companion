"""Regression: M7 mod-audit Compose content must be inside LazyColumn's item {}."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / 'app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt'


class M7ComposeLazyListRegression(unittest.TestCase):
    def test_mod_audit_composables_are_in_lazy_item(self):
        source = FILE.read_text(encoding='utf-8')
        begin = source.index('if (state.compatibilityIssues.isNotEmpty()) {')
        end = source.index('// Profiles section', begin)
        block = source[begin:end]
        self.assertIn('item {', block, 'LazyColumn requires an item builder for audit UI')
        self.assertLess(block.index('item {'), block.index('StardewCard {'))
        self.assertLess(block.index('item {'), block.index('Spacer(Modifier.height(12.dp))'))
        self.assertIn('Mod compatibility audit', block)


if __name__ == '__main__':
    unittest.main()
