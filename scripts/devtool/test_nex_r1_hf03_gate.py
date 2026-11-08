"""HF03 adversarial host source regressions, no Android SDK required."""
import unittest
import nex_r1_hf03_gate as gate

class HF03SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.ux,cls.nex,cls.runner,cls.workflow=(gate.read(p) for p in (gate.UX,gate.NEX,gate.RUN,gate.WORK))
    def check(self,**kwargs):
        fields=dict(ux=self.ux,nex=self.nex,runner=self.runner,workflow=self.workflow)
        fields.update(kwargs)
        return gate.check(**fields)
    def test_real_source_contract(self):self.assertEqual(self.check()['old_ui_test_count'],9)
    def test_old_button_text_rejected(self):
        with self.assertRaisesRegex(AssertionError,'HF03_STALE_FILTER_ACTION'):
            self.check(ux=self.ux.replace('rule.onNodeWithTag("nex.r1.filter.apply")', 'rule.onNodeWithText("Show results")'))
    def test_remove_contrast_rejected(self):
        with self.assertRaisesRegex(AssertionError,'HF03_MISSING_NONBLANK_GUARD'):
            self.check(nex=self.nex.replace('foregroundPixels >= 5', 'foregroundPixels >= 0'))
    def test_reintroduce_sparse_sampling_refused(self):
        with self.assertRaisesRegex(AssertionError,'HF03_SPARSE_SAMPLER_REINTRODUCED'):
            self.check(nex=self.nex.replace('step 12','step 41'))
    def test_evidence_must_be_saved_before_assertion(self):
        capture="""ctx.openFileOutput(path, Context.MODE_PRIVATE).use { out ->
            assertTrue(img.compress(Bitmap.CompressFormat.PNG, 100, out))
        }"""
        self.assertIn(capture,self.nex)
        n=self.nex.replace(capture,'',1).replace('println("NEX_R1_SCREENSHOT_OK:$path")',capture+'\n        println("NEX_R1_SCREENSHOT_OK:$path")',1)
        with self.assertRaisesRegex(AssertionError,'HF03_CAPTURE_NOT_RETAINED_BEFORE_CHECK'):
            self.check(nex=n)
    def test_runner_requires_failure_proof(self):
        with self.assertRaisesRegex(AssertionError,'HF03_FAILURE_EVIDENCE_NOT_ALLOWLISTED'):
            self.check(runner=self.runner.replace('for stage in mods filter; do','for stage in mods; do',1))
    def test_ci_must_run_source_regressions(self):
        with self.assertRaisesRegex(AssertionError,'HF03_CI_SOURCE_GATE_MISSING'):
            self.check(workflow=self.workflow.replace("'test_nex_r1_hf03_gate.py' -v", "'test_nex_r1_gate.py' -v"))
    def test_device_unsafe_mutation_refused(self):
        with self.assertRaisesRegex(AssertionError,'HF03_UNSAFE_TEST_ACTION'):
            self.check(nex=self.nex+'\n// startDownload(\n')

if __name__=='__main__':unittest.main()
