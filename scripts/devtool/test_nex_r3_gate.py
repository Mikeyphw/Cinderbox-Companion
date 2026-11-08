"""Negative source-gate regressions: ensure no silent weakening of offline E2E proof."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import nex_r3_gate as gate

FILES = (
    gate.ANDROID, gate.RUNNER, gate.EVIDENCE, gate.WORKFLOW, gate.DOCUMENT, gate.POLICY,
    'app/src/main/java/com/sdvsync/MainActivity.kt',
    'app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt',
    'app/src/main/java/com/sdvsync/ui/screens/ApprovedModDetailScreen.kt',
    'app/src/main/java/com/sdvsync/ui/screens/ModDetailScreen.kt',
    'app/src/main/java/com/sdvsync/mods/api/NexusModSource.kt',
)


class NexR3GateTest(unittest.TestCase):
    def fixture(self, tmp):
        root = Path(tmp)
        for name in FILES:
            src = gate.ROOT / name
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        return root

    def mutate(self, name, old, new, expected):
        with tempfile.TemporaryDirectory(prefix='nex-r3-gate-') as tmp:
            root = self.fixture(tmp)
            file = root / name
            contents = file.read_text()
            self.assertIn(old, contents)
            file.write_text(contents.replace(old, new))
            self.assertIn(expected, gate.check(root))

    def test_nominal(self):
        self.assertEqual([], gate.check())

    def test_no_fake_main_activity(self):
        self.mutate(gate.ANDROID, 'createAndroidComposeRule<MainActivity>()',
                    'createComposeRule()', 'NEX_R3_MISSING:real activity and prelaunch injection')

    def test_no_silent_network_or_unexpected_route(self):
        self.mutate(gate.ANDROID, 'NEX_R3_REFUSED_UNEXPECTED_API_PATH', 'allow-any-route',
                    'NEX_R3_MISSING:no network fixture')

    def test_missing_prelaunch_injection_rejected(self):
        self.mutate(gate.ANDROID, 'RuleChain.outerRule(fixture).around(compose)',
                    'RuleChain.outerRule(compose).around(fixture)',
                    'NEX_R3_MISSING:real activity and prelaunch injection')

    def test_missing_teardown_rejected(self):
        self.mutate(gate.ANDROID, 'unloadKoinModules(overrideModule)',
                    '/* no teardown */', 'NEX_R3_MISSING:real activity and prelaunch injection')

    def test_no_key_shortcut_rejected(self):
        self.mutate(gate.ANDROID, 'setNexusApiKey(null)', 'setNexusApiKey(FIXTURE_KEY)',
                    'NEX_R3_MISSING:synthetic-only credential and cleanup')

    def test_no_download_commands_in_test(self):
        self.mutate(gate.ANDROID, 'assertNoDownloadRequests()',
                    'assertNoDownloadRequests(); startDownload(',
                    'NEX_R3_UNSAFE_CODE:' + gate.ANDROID + ':startDownload(')

    def test_no_insecure_network_disable_in_runner(self):
        self.mutate(gate.RUNNER, 'r48_offline_gate.py', 'skip-isolation.py',
                    'NEX_R3_MISSING:offline hosted runner')

    def test_no_live_secret_in_workflow(self):
        self.mutate(gate.WORKFLOW, 'contents: read',
                    'contents: read\n# CINDERBOX_NEXUS_API_KEY',
                    'NEX_R3_LIVE_SECRET_REFERENCE_FORBIDDEN')

    def test_no_physical_release_policy(self):
        with tempfile.TemporaryDirectory(prefix='nex-r3-gate-') as tmp:
            root = self.fixture(tmp)
            file = root / gate.POLICY
            data = json.loads(file.read_text())
            data['release_enabled'] = True
            file.write_text(json.dumps(data))
            self.assertIn('NEX_R3_RELEASE_POLICY_CHANGED:release_enabled', gate.check(root))

    def test_no_synthetic_provenance_removal(self):
        self.mutate(gate.DOCUMENT, 'synthetic', 'proven-live',
                    'NEX_R3_MISSING:test is honest')

    def test_no_unsupported_delivery_mode(self):
        self.mutate(gate.WORKFLOW, 'api-level: 36', 'api-level: 35',
                    'NEX_R3_MISSING:hosted workflow')


if __name__ == '__main__':
    unittest.main(verbosity=2)
