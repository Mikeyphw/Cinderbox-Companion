#!/usr/bin/env python3
"""R48B host-only negative tests; never launch Gradle or Android locally."""
from pathlib import Path
import importlib.util
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
spec = importlib.util.spec_from_file_location('r48b_layout_gate', HERE / 'r48b_layout_gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

SOURCES = (
    'app/src/main/java/com/sdvsync/ui/components/StardewTopAppBar.kt',
    'app/src/main/java/com/sdvsync/ui/screens/HomeScreen.kt',
    'app/src/main/java/com/sdvsync/ui/components/StardewBottomBar.kt',
    'app/src/androidTest/java/com/sdvsync/qualification/R48RealActivityDeviceTest.kt',
    'docs/security/M3_RELEASE_POLICY.json',
)


class CompactHeaderTests(unittest.TestCase):
    def test_repository_contract(self):
        self.assertEqual(gate.check(), [])

    def make_fixture(self, path: Path) -> None:
        for relative in SOURCES:
            destination = path / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)

    def test_compact_flow_cannot_be_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            self.make_fixture(p)
            f = p / SOURCES[0]
            f.write_text(f.read_text().replace('FlowRow(', 'Row('))
            self.assertTrue(any('FlowRow(' in e for e in gate.check(p)))

    def test_status_and_screen_actions_must_remain_present(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            self.make_fixture(p)
            f = p / SOURCES[0]
            f.write_text(f.read_text().replace('SteamLiveBadge()\n                        actions()', 'SteamLiveBadge()'))
            self.assertTrue(gate.check(p))

    def test_flow_row_experimental_opt_in_is_mandatory(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            self.make_fixture(p)
            f = p / SOURCES[0]
            source = f.read_text()
            self.assertIn('@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)', source)
            f.write_text(source.replace(
                '@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)',
                '@OptIn(ExperimentalMaterial3Api::class)'))
            self.assertTrue(any('ExperimentalLayoutApi::class' in e for e in gate.check(p)))

    def test_release_policy_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            self.make_fixture(p)
            f = p / SOURCES[-1]
            f.write_text(f.read_text().replace('"release_enabled": false', '"release_enabled": true'))
            self.assertTrue(any('release policy' in e for e in gate.check(p)))


if __name__ == '__main__':
    unittest.main()
