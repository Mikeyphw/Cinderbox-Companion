"""Offline static guards for Android OS alias handling; Kotlin JUnit is behavioral authority."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
def load(path): return (ROOT/path).read_text()
P='app/src/main/java/com/sdvsync/'
class StorageAliasSource(unittest.TestCase):
    def test_whitelist_only_platform_prefix_components(self):
        code=load(P+'local/PlatformStoragePaths.kt')
        self.assertIn('node.path !in platformAliases',code)
        self.assertIn('Files.isSymbolicLink(node.toPath())',code)
        self.assertIn('if (!Files.exists(node.toPath()))',code)
        self.assertIn('Untrusted symbolic link: $shown',code)
        self.assertIn('InvalidPathException',code)
        self.assertIn('it == ".."',code)
        self.assertIn('"/storage/emulated/0"',code)
        self.assertIn('"/data/data"',code)
        self.assertNotIn('platformAliases.any {',code) # never prefix-match user-controlled suffix
    def test_no_legacy_full_ancestor_rejection(self):
        for path in ('local/StoragePreflight.kt','local/StoragePlanner.kt','local/M23CinderboxFirstPolicy.kt',
                     'local/M23InstallationDiscovery.kt','download/GameDownloadRecovery.kt',
                     'download/VerifiedGameRepair.kt','mods/ModSafety.kt','mods/ModProfileTransaction.kt',
                     'mods/ModBatchTransaction.kt'):
            code=load(P+path)
            self.assertIn('PlatformStoragePaths.',code,path)
            self.assertNotIn('while (node != null) {\n            if (Files.isSymbolicLink',code,path)
    def test_checkpoint_and_protection_are_preserved(self):
        recover=load(P+'download/GameDownloadRecovery.kt')
        first=load(P+'local/M23CinderboxFirstPolicy.kt')
        self.assertIn('safe.path == directory',recover)
        self.assertIn('stage.parentFile == safe.parentFile',recover)
        self.assertIn('PROTECTED_CINDERBOX_TREE',first)
        self.assertIn('primary.toPath().startsWith(target.toPath())',first)
    def test_hosted_source_ci_sees_updated_download_paths(self):
        workflow=load('.github/workflows/devtool-source-contract.yml')
        self.assertEqual(2, workflow.count("- 'app/src/main/java/com/sdvsync/download/**'"))
        self.assertEqual(2, workflow.count("- 'app/src/androidTest/java/com/sdvsync/qualification/PlatformStorageAliasDeviceTest.kt'"))

    def test_device_and_jvm_test_paths(self):
        device=load('app/src/androidTest/java/com/sdvsync/qualification/PlatformStorageAliasDeviceTest.kt')
        tests=load('app/src/test/java/com/sdvsync/local/PlatformStoragePathsTest.kt')
        self.assertIn('cacheDir.absoluteFile',device)
        self.assertIn('getExternalFilesDir(null)',device)
        self.assertIn('Files.createSymbolicLink',device)
        self.assertIn('setOf(alias.path)',tests)
        self.assertIn('"../escape"',tests)

if __name__=='__main__':unittest.main()
