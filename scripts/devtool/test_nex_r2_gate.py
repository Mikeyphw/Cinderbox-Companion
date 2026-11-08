#!/usr/bin/env python3
"""NEX-R2 source-gate regression: validate the *actual* synthetic-fixture contract."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import nex_r2_gate as gate


FILES = (
    'app/src/main/java/com/sdvsync/mods/api/NexR2Display.kt',
    'app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt',
    'app/src/main/java/com/sdvsync/ui/screens/ApprovedModDetailScreen.kt',
    'app/src/androidTest/java/com/sdvsync/ui/ux/NexR2RichDetailTest.kt',
    'scripts/devtool/nex_r2_emulator_ci.sh',
    '.github/workflows/nex-r2-rich-native.yml',
    'docs/security/M3_RELEASE_POLICY.json',
)


class NexR2SourceGateTests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        for rel in FILES:
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(gate.ROOT / rel, dest)
        return root

    def audit_changed(self, rel: str, before: str, after: str, label: str) -> None:
        with tempfile.TemporaryDirectory(prefix='nex-r2-gate-') as tmp:
            root = self.fixture(Path(tmp))
            path = root / rel
            data = path.read_text(encoding='utf-8')
            self.assertIn(before, data)
            path.write_text(data.replace(before, after), encoding='utf-8')
            self.assertIn(label, gate.check(root))

    def test_source_gate_validates_unchanged_real_fixture(self):
        self.assertEqual([], gate.check())

    def test_synthetic_fixture_disclosure_is_case_normalized(self):
        with tempfile.TemporaryDirectory(prefix='nex-r2-gate-') as tmp:
            root = self.fixture(Path(tmp))
            path = root / FILES[3]
            contents = path.read_text(encoding='utf-8')
            self.assertIn('synthetic UI fixtures', contents)
            path.write_text(contents.replace('synthetic UI fixtures', 'SYNTHETIC UI FIXTURES'), encoding='utf-8')
            self.assertEqual([], gate.check(root))

    def test_obsolete_top_level_compose_assert_exists_import_is_rejected(self):
        # assertExists() is a SemanticsNodeInteraction member, not a top-level import.
        self.audit_changed(FILES[3], 'import androidx.compose.ui.test.assertIsDisplayed',
                           'import androidx.compose.ui.test.assertExists\nimport androidx.compose.ui.test.assertIsDisplayed',
                           'NEX_R2_INVALID_COMPOSE_IMPORT:assertExists')

    def test_semantics_node_member_assert_exists_calls_remain_untouched(self):
        test = (gate.ROOT / FILES[3]).read_text(encoding='utf-8')
        self.assertNotIn('import androidx.compose.ui.test.assertExists', test)
        self.assertGreaterEqual(test.count('.assertExists()'), 5)
        self.assertEqual([], gate.check())

    def test_missing_synthetic_disclosure_is_rejected(self):
        self.audit_changed(FILES[3], 'synthetic UI fixtures', 'live verified Nexus results',
                           'NEX_R2_MISSING:synthetic fixture honesty')

    def test_implicit_download_review_is_not_mistaken_for_safe_fixture(self):
        self.audit_changed(FILES[3], 'assertEquals(0, reviews)', 'assertEquals(1, reviews)',
                           'NEX_R2_MISSING:synthetic fixture honesty')

    def test_reintroducing_obsolete_cellular_command_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='nex-r2-gate-') as tmp:
            root = self.fixture(Path(tmp))
            runner = root / FILES[4]
            runner.write_text(runner.read_text(encoding='utf-8') + '\n# svc data disable\n', encoding='utf-8')
            self.assertIn('NEX_R2_OBSOLETE_CELLULAR_SHUTDOWN', gate.check(root))

    def test_release_policy_drift_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='nex-r2-gate-') as tmp:
            root = self.fixture(Path(tmp))
            path = root / FILES[6]
            policy = json.loads(path.read_text(encoding='utf-8'))
            self.assertIs(policy.get('release_enabled'), False)
            policy['release_enabled'] = True
            path.write_text(json.dumps(policy), encoding='utf-8')
            self.assertIn('NEX_R2_RELEASE_GATE:release_enabled', gate.check(root))

    def test_browse_data_requirement_is_not_silently_dropped(self):
        self.audit_changed(FILES[1], 'NexR2Display.compactCount(', 'removedCount(',
                           'NEX_R2_MISSING:rich browse data')

    def test_unexpected_browser_engine_is_refused(self):
        with tempfile.TemporaryDirectory(prefix='nex-r2-gate-') as tmp:
            root = self.fixture(Path(tmp))
            display = root / FILES[0]
            display.write_text(display.read_text(encoding='utf-8') + '\n// WebView(\n', encoding='utf-8')
            self.assertIn('NEX_R2_FORBIDDEN:WebView(', gate.check(root))


if __name__ == '__main__':
    unittest.main(verbosity=2)
