"""M23 instrumentation source attestation negative coverage."""
from pathlib import Path
import sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m23_device_test_gate as gate

class M23AndroidDeviceSourceTests(unittest.TestCase):
    def test_constrained_test_matrix_and_no_device_claim(self):
        r=gate.generate(gate.ROOT,{})
        self.assertEqual(r['expected_case_count'],10)
        self.assertEqual(r['overall'],'PASS_SOURCE_ONLY')
        self.assertFalse(r['device_executed'])
        self.assertFalse(r['publication_allowed'])

    def test_mismatched_ci_sha_fails_closed(self):
        with self.assertRaises(gate.GateError): gate.generate(gate.ROOT,{'GITHUB_SHA':'0'*40})

    def test_replaced_or_deleted_android_test_fails_closed(self):
        old=Path.read_bytes
        def changed(self):
            out=old(self)
            if self.name=='M23DiscoveryDeviceTest.kt':return out.replace(b'm23_10',b'noop_10')
            return out
        with patch.object(Path,'read_bytes',changed):
            with self.assertRaises(gate.GateError):gate.generate(gate.ROOT,{})

    def test_same_id_with_changed_method_name_rejected(self):
        old=Path.read_bytes
        def changed(self):
            out=old(self)
            if self.name=='M23DiscoveryDeviceTest.kt':
                return out.replace(b'm23_01MissingPrivatePathsAreNotDownloadApproval',
                                   b'm23_01DifferentMethodWithSameCaseId')
            return out
        with patch.object(Path,'read_bytes',changed):
            with self.assertRaises(gate.GateError):gate.generate(gate.ROOT,{})

    def test_mutation_risk_is_rejected(self):
        old=Path.read_bytes
        def changed(self):
            out=old(self)
            if self.name=='M23DiscoveryDeviceTest.kt':return out+b'\n// pm clear\n'
            return out
        with patch.object(Path,'read_bytes',changed):
            with self.assertRaises(gate.GateError):gate.generate(gate.ROOT,{})

if __name__=='__main__':unittest.main()
