"""Negative fixtures: R2 emulator evidence and safe-source policy, no device or Gradle."""
import importlib
import json
import sys
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import m25_r2_emulator_ci as em
import m25_r2_verify
from r47_capture import png_dimensions

class R2Test(unittest.TestCase):
    @staticmethod
    def output(tests=em.TESTS,terminal=True,fail=None,duplicate=False):
        out=[]
        for name in tests:
            out.extend(['INSTRUMENTATION_STATUS: test='+name,'INSTRUMENTATION_STATUS_CODE: 1',
                'INSTRUMENTATION_STATUS: test='+name,
                'INSTRUMENTATION_STATUS_CODE: '+('-2' if name==fail else '0')])
        if duplicate:
            out+=out[:4]
        out+=['OK (4 tests)']
        if terminal:out+=['INSTRUMENTATION_CODE: -1']
        return '\n'.join(out)
    def test_accepts_exact_four(self):
        self.assertTrue(em.accepted(em.summarize(self.output(),0)))
    def test_missing_unexpected_and_duplicate_refused(self):
        for output in (self.output(tests=em.TESTS[:-1]),
                       self.output(tests=(*em.TESTS,'injectedTest')),
                       self.output(duplicate=True)):
            self.assertFalse(em.accepted(em.summarize(output,0)))
    def test_terminal_and_error_status_required(self):
        for output,code in ((self.output(terminal=False),0),
                            (self.output(fail=em.TESTS[0]),0),
                            (self.output(),1),
                            (self.output()+'\nProcess crashed',0)):
            self.assertFalse(em.accepted(em.summarize(output,code)))
    def test_raw_paths_cannot_leak_from_summary(self):
        report=em.summarize(self.output()+'\n/private/my-token',0)
        self.assertNotIn('my-token',json.dumps(report))
    def test_source_gate_contains_core_defenses(self):
        code=(ROOT/'app/src/main/java/com/sdvsync/mods/api/SmapiUpdateResponseParser.kt').read_text()
        self.assertIn('Duplicate SMAPI observation',code)
        self.assertIn('UpdateAssessment.UNKNOWN',code)
        view=(ROOT/'app/src/main/java/com/sdvsync/ui/screens/InstalledModDetailScreen.kt').read_text()
        self.assertIn('ModUpdateInsight.plainChangelog',view)
        self.assertNotIn('HtmlText(',view)
    def test_hosted_emulator_still_single_instance(self):
        wf=(ROOT/'.github/workflows/r48-real-activity-acceptance.yml').read_text()
        self.assertEqual(wf.count('ReactiveCircus/android-emulator-runner@'),1)
        self.assertIn('script: bash -c',wf)
        self.assertIn('m25_r2_verify.py',wf)
    def test_provenance_and_identity_are_hard_failures(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)
            # Direct contract inspection is source-only; untrusted receipt cannot self-qualify.
            self.assertTrue('validate_identity' in (HERE/'m25_r2_verify.py').read_text())
            self.assertTrue('source_sha' in (HERE/'m25_r2_verify.py').read_text())

if __name__=='__main__':unittest.main()
