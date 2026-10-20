import contextlib, io, json, os, subprocess, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m24_gate
import m24_device_run

class M24SourceContractTests(unittest.TestCase):
    def test_host_gate_current_source(self):
        result=m24_gate.generate()
        self.assertEqual(result['overall'],'PASS_SOURCE_ONLY')
        self.assertFalse(result['licensed_depot_manifest_verified'])
        self.assertFalse(result['device_qualified'])
    def test_false_github_sha_rejected(self):
        with self.assertRaisesRegex(ValueError,'GITHUB_SHA_MISMATCH'):
            m24_gate.generate(env={'GITHUB_SHA':'0'*40})
    def test_wrong_repository_rejected(self):
        with self.assertRaisesRegex(ValueError,'REPO_MISMATCH'):
            m24_gate.generate(env={'GITHUB_REPOSITORY':'wrong/name'})
    def test_exact_android_methods_bound(self):
        self.assertEqual(4,len(m24_gate.METHODS))
        self.assertTrue(all(x.startswith('m24_') for x in m24_gate.METHODS))
    def test_device_parser_pass(self):
        lines=[]
        for m in m24_device_run.METHODS:
            lines+=['INSTRUMENTATION_STATUS: test='+m,'INSTRUMENTATION_STATUS_CODE: 0']
        lines+=['INSTRUMENTATION_CODE: -1']
        self.assertEqual(4,m24_device_run.parse('\n'.join(lines))['completed'])
    def test_device_parser_not_false_positive(self):
        from m14_device_qualification import DeviceGateError
        lines=['INSTRUMENTATION_STATUS: test='+m24_device_run.METHODS[0],
               'INSTRUMENTATION_STATUS_CODE: 0','INSTRUMENTATION_CODE: -1']
        with self.assertRaises(DeviceGateError):m24_device_run.parse('\n'.join(lines))
if __name__=='__main__':unittest.main()
