#!/usr/bin/env python3
"""LAB05 real instrumentation receipt + source mutation negatives, no Android needed."""
from __future__ import annotations
import unittest
from pathlib import Path
from cbnx06_lab05_source_gate import ROOT, PATHS, validate, Refused
from cbnx06_lab05_receipt import CASES, case, verdict

def ok(name):
    return (f'INSTRUMENTATION_STATUS: test={name}\n'
            'INSTRUMENTATION_STATUS_CODE: 1\n'
            f'INSTRUMENTATION_STATUS: test={name}\n'
            'INSTRUMENTATION_STATUS_CODE: 0\n'
            'OK (1 test)\nINSTRUMENTATION_CODE: -1\n')

class Lab05Negatives(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.source=[(ROOT/path).read_text() for path in PATHS]
    def change(self,index,old,new,reason):
        parts=list(self.source)
        self.assertIn(old,parts[index]);parts[index]=parts[index].replace(old,new,1)
        with self.assertRaisesRegex(Refused,reason):validate(*parts)
    def test_valid_source(self):self.assertTrue(validate(*self.source))
    def test_hf02_custom_lab_host_dependency_guard(self):
        # Debug is not cbnxLab; test-host manifest must be bound to the LAB variant.
        self.change(5,'add("cbnxLabImplementation", "androidx.compose.ui:ui-test-manifest")',
                    '// dropped LAB-only host','HF02_LAB_COMPOSE_HOST_DEPENDENCY_MISSING')
    def test_hf02_host_not_in_runner_manifest(self):
        self.change(1,'androidx.compose.ui.test.junit4.android.AndroidComposeTestActivity',
                    'com.example.MissingTestActivity','HF02_HOSTED_MANIFEST_PREFLIGHT_MISSING')
    def test_hf02_runtime_manifest_check_is_required(self):
        self.change(1,'dump xmltree','dump badging',
                    'HF02_HOSTED_MANIFEST_PREFLIGHT_MISSING')
    def test_hf02_redacted_failure_category(self):
        from cbnx06_lab05_receipt import diagnostic_category
        self.assertEqual(diagnostic_category('AndroidComposeTestActivity /storage/secret TOKEN'),
                         'COMPOSE_HOST_ACTIVITY')
        self.assertEqual(diagnostic_category('NoComposeHierarchiesFoundException secret'),
                         'COMPOSE_TREE_ABSENT')
        self.assertEqual(diagnostic_category('No activities found to launch'),
                         'COMPOSE_HOST_ACTIVITY')
        self.assertEqual(diagnostic_category('some.other.Failure password'), 'UNKNOWN')
        observed=case(CASES[0], 'INSTRUMENTATION_STATUS: stack=No activities found to launch ' +
                      '/storage/secret TOKEN\nFAILURES!!!',1)
        self.assertEqual(observed['failure_category'],'COMPOSE_HOST_ACTIVITY')
        self.assertNotIn('secret',repr(observed))
        self.assertNotIn('TOKEN',repr(observed))
    def test_hf01_unsupported_compose_imports_are_refused(self):
        for symbol in ('assertExists','assertDoesNotExist'):
            self.change(0,
                'import androidx.compose.ui.test.assertIsNotEnabled',
                'import androidx.compose.ui.test.' + symbol + '\n' +
                'import androidx.compose.ui.test.assertIsNotEnabled',
                'HF01_INVALID_COMPOSE_ASSERTION_IMPORT')
    def test_hf01_node_assertions_cannot_be_deleted(self):
        self.change(0,'.assertDoesNotExist()', '.assertExists()',
                    'HF01_NODE_ASSERTIONS_REMOVED')
    def test_roster_shrunk(self):self.change(0,'@Test fun cancelSyntheticInstallDoesNotWriteModsOrJournal()',
                '@Test fun skippedCase()', 'INSTRUMENTATION_ROSTER_DRIFT')
    def test_no_private_root(self):self.change(0,'CinderboxLabBoundary.requireModsRoot(mods())',
                '// removed', 'UI_TEST_GUARD_MISSING')
    def test_consent_disabled_guard(self):self.change(0,'assertIsNotEnabled()',
                'assertIsEnabled()', 'CONSENT_ASSERTION_COUNT_DRIFT')
    def test_no_cancel_button(self):self.change(0,'cbnx06.lab04.cancel-action',
                'cbnx06.lab04.confirm-action', 'UI_TEST_GUARD_MISSING')
    def test_inject_real_storage(self):self.change(0,'private fun mods(): File = File(CinderboxPaths.MODS_DIR)',
                'private fun mods(): File = File("/storage/emulated/0/StardewValley")', 'UNSAFE_TEST')
    def test_no_emulator(self):self.change(1,'ro.kernel.qemu','ro.product.device','EMULATOR_BOUNDARY_MISSING')
    def test_no_prod_absence_check(self):self.change(1,'shell pm path com.sdvsync','shell pm path foo',
                'EMULATOR_BOUNDARY_MISSING')
    def test_no_log_cleanup(self):self.change(1,"trap 'rm -rf -- \"$rawdir\"' EXIT",'trap : EXIT',
                'RUNNER_GUARD_MISSING')
    def test_unpinned_runner(self):self.change(3,'test "$(git rev-parse HEAD)" = "$CBNX_LAB05_HEAD_SHA"',
                'true','HOSTED_SOURCE_PIN_COUNT_DRIFT')
    def test_android_variant(self):self.change(3,'-PcbnxLabAndroidTest=true','-PcbnxWrong=true',
                'HOSTED_WORKFLOW_MISSING')
    def test_full_lab_unwired(self):self.change(4,'python3 -B scripts/devtool/cbnx06_lab05_tests.py',
                'echo skipped', 'FULL_LAB_INHERITANCE_MISSING')
    def test_result_valid(self):
        d=verdict({n:(ok(n),0) for n in CASES},'a'*40,'123','b'*64,'c'*64)
        self.assertEqual(d['status'],'PASS');self.assertEqual(d['tests_passed'],4)
        self.assertEqual(d['actual_test_count'],4);self.assertFalse(d['physical_qualified'])
        self.assertFalse(d['release_qualified']);self.assertFalse(d['live_iceraven_qualified'])
    def test_wrong_test_even_if_ok(self):
        a=case(CASES[0],ok(CASES[1]),0)
        self.assertEqual(a['status'],'NOT_QUALIFIED')
        self.assertEqual(a['reason'],'TEST_EVENTS_MISSING')
    def test_status_minus_two_rejected(self):
        a=case(CASES[0],ok(CASES[0]).replace('INSTRUMENTATION_STATUS_CODE: 0',
                 'INSTRUMENTATION_STATUS_CODE: -2'),0)
        self.assertEqual(a['status'],'NOT_QUALIFIED')
    def test_wrong_terminal_result(self):
        self.assertNotEqual(case(CASES[0],ok(CASES[0]).replace('INSTRUMENTATION_CODE: -1',
                  'INSTRUMENTATION_CODE: 0'),0)['status'],'PASS')
    def test_timeout(self):self.assertEqual(case(CASES[0],'timeout',124)['reason'],'TIMEOUT')
    def test_redacted_failure(self):
        raw='INSTRUMENTATION_STATUS: stack=TOKEN /storage/private\n  at CbNxLab05UiJourneyTest.kt:123\nFAILURES!!!'
        result=case(CASES[0],raw,1)
        self.assertEqual(result['site'],'CbNxLab05UiJourneyTest:123')
        self.assertNotIn('TOKEN',str(result));self.assertNotIn('/storage',str(result))
    def test_incomplete_aggregate(self):
        inputs={n:(ok(n),0) for n in CASES};inputs[CASES[3]]=('',1)
        self.assertEqual(verdict(inputs,'a'*40,'123','b'*64,'c'*64)['tests_passed'],3)
    def test_case_roster_changed(self):
        with self.assertRaises(AssertionError):
            verdict({CASES[0]:(ok(CASES[0]),0)},'a'*40,'123','b'*64,'c'*64)
    def test_invalid_sha(self):
        with self.assertRaises(AssertionError):
            verdict({n:(ok(n),0) for n in CASES},'BAD','123','b'*64,'c'*64)

if __name__=='__main__':unittest.main(verbosity=2)
