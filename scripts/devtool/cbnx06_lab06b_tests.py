#!/usr/bin/env python3
"""LAB06B policy/receipt adversarial tests: real source mutations, no Android access."""
from __future__ import annotations
import unittest
from cbnx06_lab06b_source_gate import ROOT,PATHS,EXPECTED,validate,Refused
from cbnx06_lab06b_receipt import CASES,classify,verdict,redacted_category


def passing(name):
    return (f'INSTRUMENTATION_STATUS: test={name}\n'
            'INSTRUMENTATION_STATUS_CODE: 1\n'
            f'INSTRUMENTATION_STATUS: test={name}\n'
            'INSTRUMENTATION_STATUS_CODE: 0\n'
            'OK (1 test)\nINSTRUMENTATION_CODE: -1\n')

class Lab06BNegatives(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.src=[(ROOT/p).read_text(encoding='utf8') for p in PATHS]
    def change(self,index,old,new,reason):
        x=list(self.src)
        self.assertIn(old,x[index]);x[index]=x[index].replace(old,new,1)
        with self.assertRaisesRegex(Refused,reason):validate(*x)
    def test_01_baseline(self):self.assertTrue(validate(*self.src))
    def test_02_wrong_test_case(self):self.change(0,'@Test fun changedArchiveBytesCannotReachMods()','@Test fun differentCase()','FIVE_CASE_ROSTER_DRIFT')
    def test_03_missing_isolation(self):self.change(0,'CinderboxLabBoundary.requireModsRoot(mods())','// removed','LAB_ISOLATION_GUARD_MISSING')
    def test_04_wrong_package(self):self.change(0,'BuildConfig.CBNX_LAB','true','TEST_SAFETY_GUARD_MISSING')
    def test_05_missing_archive_tamper(self):self.change(0,'zip.appendBytes(byteArrayOf(1))','// skipped','TEST_SAFETY_GUARD_MISSING')
    def test_06_forged_provenance_not_tested(self):self.change(0,'record.put("nexus_file_provenance_verified", true)','// skipped','TEST_SAFETY_GUARD_MISSING')
    def test_07_wrong_approval_not_tested(self):self.change(0,'"LAB06B_INVALID_APPROVAL_KEY"','"APPROVED"','TEST_SAFETY_GUARD_MISSING')
    def test_08_no_recovery_journal(self):self.change(0,'.put("state", "INSTALLING")','.put("state", "INSTALLED")','INTERRUPTED_JOURNAL_FIXTURE_DRIFT')
    def test_09_replay_not_tested(self):self.change(0,'refuse { NexusLab04SyntheticTransaction.rollbackSynthetic(context) }','// replay not checked','ROLLBACK_REFUSAL_CASE_COUNT_DRIFT')
    def test_10_no_failure_assertion(self):self.change(0,'fail("LAB06B_EXPECTED_REFUSAL")','return','TEST_SAFETY_GUARD_MISSING')
    def test_11_plain_synthetic_root(self):self.change(0,'private fun mods() = File(CinderboxPaths.MODS_DIR)',
          'private fun mods() = File("/storage/emulated/0/StardewValley/desktop/Mods")','FORBIDDEN_DEVICE_TEST_CAPABILITY')
    def test_12_no_qemu_gate(self):self.change(1,'ro.kernel.qemu','ro.product.device','RUNNER_GUARD_MISSING')
    def test_13_wrong_sdk(self):self.change(1,'" = 36','" = 35','RUNNER_GUARD_MISSING')
    def test_14_prod_package_danger(self):self.change(1,'pm clear com.sdvsync.cbnx06lab','pm clear com.sdvsync ','RUNNER_GUARD_MISSING')
    def test_15_reset_removed(self):self.change(1,'test "$cleared" = Success','true','RUNNER_GUARD_MISSING')
    def test_16_prod_package_absence_check(self):self.change(1,'shell pm path com.sdvsync 2>/dev/null','shell pm path wrong 2>/dev/null','RUNNER_GUARD_MISSING')
    def test_17_no_raw_cleanup(self):self.change(1,"trap 'rm -rf -- \"$rawdir\"' EXIT",'trap : EXIT','RUNNER_GUARD_MISSING')
    def test_18_wrong_instrumentation_class(self):self.change(1,'CbNxLab06bNegativeDeviceTest#$method','FakeDeviceTest#$method','RUNNER_MISSING_EXACT_CLASS')
    def test_19_ci_unpinned(self):self.change(3,'test "$(git rev-parse HEAD)" = "$CBNX_LAB06B_HEAD_SHA"','true','CI_HEAD_PIN_COUNT_DRIFT')
    def test_20_no_android_compile(self):self.change(3,':app:assembleCbnxLabAndroidTest',':app:assembleDebugAndroidTest','CI_CONTRACT_MISSING')
    def test_21_wrong_api(self):self.change(3,'api-level: 36','api-level: 35','CI_CONTRACT_MISSING')
    def test_22_full_lab_not_wired(self):self.change(4,'python3 -B scripts/devtool/cbnx06_lab06b_tests.py','echo skip','FULL_LAB_GATE_MISSING')
    def test_23_missing_original_transaction(self):self.change(6,'CinderboxLabBoundary.requireModsRoot(mods)','// deleted','EXISTING_TRANSACTION_SAFETY_LOST')
    def test_24_missing_existing_provenance(self):self.change(7,'!previous.getBoolean("nexus_file_provenance_verified")','true','EXISTING_STAGING_SAFETY_LOST')
    def test_25_no_physical_scope(self):self.change(5,'Synthetic only','External only','DOCUMENT_SCOPE_MISSING')
    def test_26_all_tests_exactly_pass(self):
        d=verdict({x:(passing(x),0) for x in CASES},'a'*40,'123','b'*64,'c'*64)
        self.assertEqual(d['status'],'PASS');self.assertEqual(d['tests_passed'],5)
        self.assertEqual(d['actual_test_count'],5)
        self.assertFalse(d['physical_qualified']);self.assertFalse(d['live_iceraven_qualified'])
        self.assertFalse(d['release_qualified']);self.assertFalse(d['nexus_file_provenance_verified'])
    def test_27_missing_case_denied(self):
        with self.assertRaises(AssertionError):verdict({CASES[0]:(passing(CASES[0]),0)},'a'*40,'123','b'*64,'c'*64)
    def test_28_wrong_identity_even_if_pass_count_ok(self):
        d=classify(CASES[0],passing(CASES[1]),0)
        self.assertEqual(d['status'],'NOT_QUALIFIED')
        self.assertEqual(d['reason'],'TEST_EVENTS_MISSING')
    def test_29_terminal_code_not_success(self):
        x=classify(CASES[0],passing(CASES[0]).replace('INSTRUMENTATION_CODE: -1','INSTRUMENTATION_CODE: 0'),0)
        self.assertEqual(x['status'],'NOT_QUALIFIED')
    def test_30_failed_case_blocks_verdict(self):
        data={x:(passing(x),0) for x in CASES}
        data[CASES[-1]]=('FAILURES!!!',1)
        x=verdict(data,'a'*40,'123','b'*64,'c'*64)
        self.assertEqual(x['status'],'NOT_QUALIFIED');self.assertEqual(x['tests_passed'],4)
    def test_31_timeout_not_success(self):self.assertEqual(classify(CASES[0],'timeout',124)['reason'],'TIMEOUT')
    def test_32_code_site_is_redacted(self):
        raw='INSTRUMENTATION_STATUS: stack=token /storage/private/\n  at CbNxLab06bNegativeDeviceTest.kt:123\nFAILURES!!!'
        x=classify(CASES[0],raw,1)
        self.assertEqual(x['site'],'CbNxLab06bNegativeDeviceTest:123')
        self.assertNotIn('token',repr(x));self.assertNotIn('/storage',repr(x))
    def test_33_failure_category_has_no_raw_log(self):
        self.assertEqual(redacted_category('LAB06B_STALE_JOURNAL /secret password'),'STALE_TEST_FIXTURE')
        self.assertEqual(redacted_category('sensitive bytes'), 'UNKNOWN')
    def test_34_truncated_log(self):self.assertEqual(classify(CASES[0],'x'*524289,0)['reason'],'LOG_BUDGET')
    def test_35_unbound_sha(self):
        with self.assertRaises(AssertionError):verdict({x:(passing(x),0) for x in CASES},'bad','123','b'*64,'c'*64)
    def test_36_minus_two_denied(self):
        self.assertNotEqual(classify(CASES[0],passing(CASES[0]).replace('INSTRUMENTATION_STATUS_CODE: 0','INSTRUMENTATION_STATUS_CODE: -2'),0)['status'],'PASS')
    def test_37_roster_matches_receipt(self):self.assertEqual(tuple(EXPECTED),tuple(CASES))

if __name__=='__main__':unittest.main(verbosity=2)
