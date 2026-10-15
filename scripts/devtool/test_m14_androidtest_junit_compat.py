"""M14 instrumentation must compile with the pinned androidx.test JUnit4 dependency."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
TEST = ROOT / 'app/src/androidTest/java/com/sdvsync/qualification/M14IsolatedDeviceTest.kt'
GRADLE = ROOT / 'app/build.gradle.kts'

class AndroidJUnitCompatibility(unittest.TestCase):
    def test_no_androidtest_uses_unavailable_assertthrows(self):
        for path in (ROOT / 'app/src/androidTest').rglob('*.kt'):
            self.assertNotIn('assertThrows(', path.read_text(encoding='utf8'), str(path))

    def test_explicit_expected_failure_preserves_rollback_assertions(self):
        content = TEST.read_text(encoding='utf8')
        self.assertIn('fail("Expected the interrupted multi-mod transaction to fail")', content)
        self.assertIn('catch (_: IllegalStateException)', content)
        self.assertIn('assertEquals("kept", File(mods, "alpha/old.txt").readText())', content)
        self.assertIn('assertFalse(File(mods, "beta").exists())', content)
        self.assertIn('assertTrue(tx.recover())', content)

    def test_android_fixture_resolves_platform_cache_alias_without_loosening_production_paths(self):
        content = TEST.read_text(encoding='utf8')
        self.assertIn('targetContext.cacheDir.canonicalFile', content)
        self.assertIn('createTempDirectory(cache.toPath(), "m14-device-").toFile().canonicalFile', content)
        self.assertIn('root.parentFile == cache', content)
        self.assertIn('!Files.isSymbolicLink(ancestor.toPath())', content)
        self.assertIn('"Fixture escaped app-private cache"', content)
        self.assertIn('".m14-test-owned"', content)
        self.assertIn('root.deleteRecursively()', content)
        self.assertNotIn('targetContext.filesDir', content)

    def test_unknown_storage_budget_never_claims_capacity_sufficient(self):
        content = TEST.read_text(encoding='utf8')
        self.assertIn('StoragePlanner.downloadPlan(root, null)', content)
        self.assertIn('assertNull(budget.payloadBytes)', content)
        self.assertIn('assertNull(budget.requiredBytes)', content)
        self.assertIn('assertFalse(budget.sufficient == true)', content)
        self.assertNotIn('assertNull(budget.sufficient)', content)

    def test_existing_instrumentation_junit_dependency_remains(self):
        self.assertIn('androidTestImplementation("androidx.test.ext:junit:1.2.1")',
                      GRADLE.read_text(encoding='utf8'))

if __name__ == '__main__':
    unittest.main()
