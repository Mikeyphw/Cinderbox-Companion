"""New Cinderbox-first policy/Devtool evidence checks; never accesses user files."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m23_discovery_gate as gate
from m14_device_qualification import DeviceGateError
import m23_cinderbox_first_device_run as device


def raw(methods=device.METHODS, fail=None):
    lines=[]
    for method in methods:
        lines += ['INSTRUMENTATION_STATUS: test='+method,
                  'INSTRUMENTATION_STATUS_CODE: '+('-2' if method==fail else '0')]
    return '\n'.join(lines+['INSTRUMENTATION_CODE: -1'])+'\n'

class CinderboxFirstSourceTests(unittest.TestCase):
    def test_source_inventory_passes_with_fail_closed_flags(self):
        result=gate.generate(gate.ROOT,{})
        self.assertEqual(result['overall'],'PASS_M23_SOURCE_INVENTORY')
        self.assertTrue(result['safety']['primary_cinderbox_tree_write_protected'])
        self.assertFalse(result['m23_device_qualified'])

    def test_new_three_case_android_source_manifest_is_separate(self):
        import m23_device_test_gate as device_gate
        result=device_gate.generate(device_gate.ROOT,{})
        self.assertEqual(result['expected_case_count'],10)
        self.assertEqual(result['cinderbox_integration_case_count'],3)
        self.assertFalse(result['device_executed'])

    def test_policy_guard_removal_rejected(self):
        original=gate.safe
        def altered(root,path):
            content=original(root,path)
            if path.endswith('M23CinderboxFirstPolicy.kt'):
                return content.replace(b'val authorizesDownload: Boolean = false',
                                       b'val authorizesDownload: Boolean = true')
            return content
        with patch.object(gate,'safe',side_effect=altered):
            with self.assertRaises(gate.GateError):gate.generate(gate.ROOT,{})

    def test_exact_android_methods_pass(self):
        s=device.parse(raw())
        self.assertEqual(s['completed'],3)
        self.assertEqual(s['cases'],{k:'PASS' for k in device.IDS})

    def test_failed_method_is_retained_not_overridden(self):
        with self.assertRaises(DeviceGateError) as caught:
            device.parse(raw(fail=device.METHODS[1]))
        self.assertEqual(caught.exception.case_summary['cases']['m23cb_02'],'FAIL')

    def test_missing_android_method_stays_incomplete(self):
        with self.assertRaises(DeviceGateError) as caught:
            device.parse(raw(methods=device.METHODS[:-1]))
        self.assertEqual(caught.exception.case_summary['cases']['m23cb_03'],'NOT_COMPLETED')

if __name__=='__main__':unittest.main()
