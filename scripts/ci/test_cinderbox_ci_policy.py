#!/usr/bin/env python3
"""Offline classification, cadence and security regression checks."""
from pathlib import Path
from unittest import TestCase, main, mock
import importlib.util
import subprocess
import tempfile

MODULE = Path(__file__).with_name('cinderbox_ci_policy.py')
spec = importlib.util.spec_from_file_location('cinderbox_ci_policy', MODULE)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)

class ClassificationTests(TestCase):
    def test_docs_never_compile_android(self):
        x = policy.classify(['docs/CBNX02B.md'])
        self.assertFalse(x['needs_android'])
        self.assertEqual(x['source_gates'], [])

    def test_download_queue_runs_source_guards_and_android(self):
        x = policy.classify(['app/src/main/java/com/sdvsync/mods/ModDownloadService.kt'])
        self.assertTrue(x['needs_android'])
        self.assertIn('cbnx02_source_gate.py', x['source_gates'])
        self.assertIn('cbnx01_gate.py', x['source_gates'])

    def test_nexus_viewmodel_and_bridge_are_safety_scoped(self):
        x = policy.classify(['app/src/main/java/com/sdvsync/mods/api/NexusBrowserHandoff.kt'])
        self.assertIn('nex_r5_gate.py', x['source_gates'])
        self.assertIn('cbnx01_gate.py', x['source_gates'])

    def test_unknown_android_fails_closed_to_broad_contracts(self):
        x = policy.classify(['app/src/main/java/com/sdvsync/unknown/BrandNew.kt'])
        self.assertTrue(x['needs_android'])
        self.assertIn('nex_r5_gate.py', x['source_gates'])
        self.assertIn('r43c_gate.py', x['source_gates'])

    def test_workflow_edit_runs_all_source_gates_but_not_android(self):
        x = policy.classify(['.github/workflows/build.yml'])
        self.assertTrue(x['ci_sensitive'])
        self.assertFalse(x['needs_android'])
        self.assertIn('cbnx02_source_gate.py', x['source_gates'])

    def test_deleted_gate_is_not_silently_ignored(self):
        x = policy.classify(['scripts/ci/cinderbox_ci_policy.py'])
        self.assertIn('nex_r5_gate.py', x['source_gates'])

class SourceTestRunnerTests(TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(prefix='cbnx-ci-source-tests-')
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        (self.root / 'scripts/devtool').mkdir(parents=True)

    def source(self, filename, code):
        path = self.root / 'scripts/devtool' / filename
        path.write_text(code, encoding='utf-8')
        return path

    def test_nxm_standalone_assertions_are_executed_not_skipped(self):
        name = 'test_cbnx01_nxm_ingress.py'
        self.source(name, 'from pathlib import Path\nPath("witness.txt").write_text("executed")\n')
        policy.run_source_test(name, self.root)
        self.assertEqual((self.root / 'witness.txt').read_text(), 'executed')

    def test_nxm_standalone_failure_blocks_qualification(self):
        name = 'test_cbnx01_nxm_ingress.py'
        self.source(name, 'raise AssertionError("credential exposed")\n')
        with self.assertRaises(subprocess.CalledProcessError):
            policy.run_source_test(name, self.root)

    def test_class_based_regression_is_discovered_and_executed(self):
        name = 'test_ux08a_gate.py'
        self.source(name, 'import unittest\nclass T(unittest.TestCase):\n'
                          '    def test_real(self):\n'
                          '        __import__("pathlib").Path("witness.txt").write_text("unit")\n')
        policy.run_source_test(name, self.root)
        self.assertEqual((self.root / 'witness.txt').read_text(), 'unit')

    def test_empty_unittest_suite_fails_instead_of_silent_pass(self):
        name = 'test_ux08a_gate.py'
        self.source(name, 'print("zero tests")\n')
        with self.assertRaises(subprocess.CalledProcessError):
            policy.run_source_test(name, self.root)

    def test_missing_linked_and_unlisted_tests_refused(self):
        name = 'test_ux08a_gate.py'
        with self.assertRaisesRegex(RuntimeError, 'MISSING_SOURCE_TEST'):
            policy.run_source_test(name, self.root)
        self.source(name, 'import unittest\n')
        (self.root / 'scripts/devtool' / name).unlink()
        (self.root / 'scripts/devtool' / name).symlink_to(self.root / 'witness.txt')
        with self.assertRaisesRegex(RuntimeError, 'MISSING_SOURCE_TEST'):
            policy.run_source_test(name, self.root)
        with self.assertRaisesRegex(RuntimeError, 'SOURCE_TEST_UNLISTED'):
            policy.run_source_test('untrusted.py', self.root)

class GateTests(TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(prefix='cbnx-ci-unit-')
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.git('init', '-q', '-b', 'master')
        self.git('config', 'user.name', 'Test Only')
        self.git('config', 'user.email', 'test@example.invalid')
        self.commit('README.md', 'baseline')
        self.base = self.git('rev-parse', 'HEAD')
        self.p = mock.patch.object(policy, 'INITIAL_BASELINE', self.base)
        self.p.start()
        self.addCleanup(self.p.stop)

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True).strip()

    def commit(self, path, contents):
        f = self.root / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(contents, encoding='utf-8')
        self.git('add', '--', path)
        self.git('commit', '-q', '-m', 'synthetic overlay')

    def plan(self, **kw):
        return policy.gate_plan(self.git('rev-parse', 'HEAD'), cwd=self.root, **kw)

    def test_not_due_before_fifth_mainline_commit(self):
        for n in range(4):
            self.commit(f'docs/{n}.txt', str(n))
        self.assertFalse(self.plan()['due'])
        self.assertEqual(self.plan()['first_parent_units'], 4)
        self.commit('docs/fifth.txt', '5')
        self.assertTrue(self.plan()['due'])
        self.assertIn('cadence', self.plan()['reasons'])

    def test_ordinary_service_change_not_emergency_gate(self):
        self.commit('app/src/main/java/com/sdvsync/mods/ModDownloadService.kt', 'safe code')
        self.assertFalse(self.plan()['due'])

    def test_release_policy_change_immediate_full_gate(self):
        self.commit('docs/security/M3_RELEASE_POLICY.json', '{}')
        self.assertIn('security-sensitive', self.plan()['reasons'])

    def test_successful_gate_tag_resets_counter(self):
        self.commit('docs/a.txt', 'a')
        head = self.git('rev-parse', 'HEAD')
        self.git('tag', 'cinderbox-full-gate/123', head)
        self.assertEqual(self.plan()['first_parent_units'], 0)
        self.commit('docs/b.txt', 'b')
        self.assertEqual(self.plan()['first_parent_units'], 1)

    def test_non_mainline_tag_does_not_reset_counter(self):
        self.git('checkout', '-q', '-b', 'other')
        self.commit('docs/side.txt', 'side')
        self.git('tag', 'cinderbox-full-gate/rogue')
        self.git('checkout', '-q', 'master')
        self.commit('docs/main.txt', 'main')
        self.assertEqual(self.plan()['first_parent_units'], 1)

    def test_manual_forces_gate(self):
        self.assertTrue(self.plan(force=True)['due'])

    def test_invalid_cadence_refused(self):
        for n in (0, 26, -1):
            with self.assertRaises(ValueError):
                self.plan(interval=n)

    def test_wrong_baseline_refused(self):
        with mock.patch.object(policy, 'INITIAL_BASELINE', 'f' * 40):
            with self.assertRaises(RuntimeError):
                self.plan()

    def test_expected_jobs_are_nonempty_and_explicit(self):
        self.assertEqual(len(policy.REQUIRED), 6)
        self.assertTrue(all(policy.REQUIRED.values()))

if __name__ == '__main__':
    main(verbosity=2)
