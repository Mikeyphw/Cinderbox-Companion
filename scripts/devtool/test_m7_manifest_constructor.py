"""Guard M7A's Kotlin ModManifest JVM fixture against omitted required args."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class M7ModManifestConstructorRegression(unittest.TestCase):
    def test_required_description_is_present(self):
        source = (ROOT / 'app/src/test/java/com/sdvsync/mods/ModCompatibilityTest.kt').read_text('utf-8')
        self.assertIn('ModManifest(id, "Test", version, id, description = "", dependencies = deps, contentPackFor = pack)', source)
        self.assertNotIn('ModManifest(id, "Test", version, id, dependencies = deps, contentPackFor = pack)', source)

    def test_model_still_requires_description(self):
        models = (ROOT / 'app/src/main/java/com/sdvsync/mods/models/ModModels.kt').read_text('utf-8')
        self.assertIn('data class ModManifest(', models)
        self.assertIn('val description: String,', models)

    def test_jvm_tests_remain_in_ci(self):
        for path in ('.github/workflows/build.yml', '.github/workflows/devtool-android-build.yml'):
            workflow = (ROOT / path).read_text('utf-8')
            self.assertIn('testDebugUnitTest', workflow)


if __name__ == '__main__':
    unittest.main()
