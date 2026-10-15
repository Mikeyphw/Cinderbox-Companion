"""Guard against Kotlin preview references to an out-of-scope M9 variable."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

class M9PreviewKotlinSourceContract(unittest.TestCase):
    def test_preview_uses_declared_match_collection_not_removed_existing_variable(self):
        source = (ROOT / 'app/src/main/java/com/sdvsync/mods/ModFileManager.kt').read_text(encoding='utf-8')
        preview = source.split('            val changes = manifests.map { manifestFile ->', 1)[1].split(
            '            return ModArchivePreview(digest, changes,', 1)[0]
        self.assertIn('val matches = currentMods.filter', preview)
        self.assertIn('require(matches.size <= 1)', preview)
        self.assertIn('check(!target.exists() || matches.isNotEmpty())', preview)
        self.assertNotIn('check(!target.exists() || existing != null)', preview)

if __name__ == '__main__': unittest.main()
