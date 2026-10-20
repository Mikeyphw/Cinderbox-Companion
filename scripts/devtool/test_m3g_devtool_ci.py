"""M3G Devtool ACTIONS-05 CI contract checks; dependency-free."""
import pathlib
import unittest

from ci_workflow_contract import effective_ci_source
ROOT = pathlib.Path(__file__).resolve().parents[2]
FLOW = ROOT / '.github/workflows/devtool-android-build.yml'
CI = ROOT / 'scripts/devtool/m3g_devtool_ci.sh'

class DevtoolActionsContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = effective_ci_source(ROOT,'.github/workflows/devtool-android-build.yml')
        cls.script = CI.read_text()

    def test_dispatch_entrypoint(self):
        self.assertIn('workflow_dispatch:', self.workflow)
        for name in ('project_dir:', 'module:', 'variant:', 'format:'):
            self.assertIn(name, self.workflow)

    def test_debug_only(self):
        self.assertIn("options: ['debug']", self.workflow)
        self.assertIn("options: ['apk']", self.workflow)
        self.assertIn("default: 'native-only'", self.workflow)
        self.assertNotIn('DEVTOOL_RELEASE_KEYSTORE', self.workflow)

    def test_android_toolchain(self):
        self.assertIn("java-version: '17'", self.workflow)
        self.assertIn("'platforms;android-35'", self.workflow)

    def test_android_ci_tests_before_artifact(self):
        self.assertIn('./gradlew testDebugUnitTest lintDebug assembleDebug', self.workflow)
        self.assertIn('invoke --target cinderbox build', self.workflow)
        self.assertIn('name: devtool-android-debug-apk', self.workflow)
        self.assertLess(self.workflow.index('Test, lint, and build debug APK'), self.workflow.index('Stage original Devtool manual fallback artifact'))

    def test_read_only_permission_and_no_release_publication(self):
        self.assertIn('contents: read', self.workflow)
        self.assertNotIn('releases/create', self.workflow)
        self.assertNotIn('id-token: write', self.workflow)

    def test_devtool_source_binding(self):
        self.assertIn('actions android plan', self.script)
        self.assertIn('actions android run', self.script)
        self.assertIn('--ref "$branch"', self.script)
        self.assertIn('--yes --json', self.script)

    def test_devtool_read_and_collect(self):
        for value in ('actions watch', 'actions artifacts', 'actions android collect'):
            self.assertIn(value, self.script)
        self.assertIn('--expected-package com.sdvsync --download --json', self.script)

    def test_workflow_extends_preexisting_m3_evidence(self):
        self.assertIn('m3_build_evidence.py generate', self.workflow)
        self.assertIn("'test_m3g_*.py'", self.workflow)
        self.assertIn('GITHUB_SHA', self.workflow)
        pr = (ROOT / '.github/workflows/build.yml').read_text()
        self.assertIn("'test_m3g_*.py'", pr)
        self.assertIn('pull_request:', pr)

    def test_no_auto_install_or_release_signing(self):
        self.assertNotIn('adb install', self.script)
        self.assertNotIn('assembleRelease', self.workflow)

if __name__ == '__main__':
    unittest.main()
