"""M23 runner full-method-name parsing regressions (never invokes adb)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from m14_device_qualification import DeviceGateError
from m23_device_run import parse_m23_instrumentation
from m23_device_test_gate import METHODS, EXPECTED


def instrument(methods=METHODS, failure=None, final=-1):
    out=[]
    for method in methods:
        out.extend(('INSTRUMENTATION_STATUS: class=com.sdvsync.qualification.M23DiscoveryDeviceTest',
                    'INSTRUMENTATION_STATUS: test='+method,
                    'INSTRUMENTATION_STATUS_CODE: 1',
                    'INSTRUMENTATION_STATUS: test='+method,
                    'INSTRUMENTATION_STATUS_CODE: '+ ('-2' if failure==method else '0')))
    out.append(f'INSTRUMENTATION_CODE: {final}')
    return '\n'.join(out)+'\n'


class M23RunnerParsingTests(unittest.TestCase):
    def test_all_exact_junit_methods_pass(self):
        result=parse_m23_instrumentation(instrument())
        self.assertEqual(result['completed'],10)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['cases'], {c:'PASS' for c in EXPECTED})
        self.assertTrue(result['parsed_using_full_method_names'])

    def test_one_actual_failure_is_correctly_attributed(self):
        with self.assertRaises(DeviceGateError) as caught:
            parse_m23_instrumentation(instrument(failure=METHODS[3]))
        self.assertEqual(caught.exception.code,'INSTRUMENTATION_INCOMPLETE_OR_FAILED')
        cases=caught.exception.case_summary['cases']
        self.assertEqual(cases['m23_04'],'FAIL')
        self.assertEqual(sum(v=='PASS' for v in cases.values()),9)

    def test_missing_method_cannot_be_accepted(self):
        with self.assertRaises(DeviceGateError) as caught:
            parse_m23_instrumentation(instrument(methods=METHODS[:-1]))
        self.assertEqual(caught.exception.case_summary['cases']['m23_10'],'NOT_COMPLETED')

    def test_no_instrumentation_output_remains_blocked(self):
        with self.assertRaises(DeviceGateError) as caught:
            parse_m23_instrumentation('INSTRUMENTATION_CODE: -1\n')
        self.assertEqual(caught.exception.case_summary['completed'],0)
        self.assertEqual(len(caught.exception.case_summary['cases']),10)

    def test_unexpected_method_names_cannot_pass(self):
        with self.assertRaises(DeviceGateError) as caught:
            parse_m23_instrumentation(instrument(methods=EXPECTED))
        self.assertEqual(caught.exception.case_summary['completed'],0)

    def test_non_success_instrumentation_exit_fails(self):
        with self.assertRaises(DeviceGateError):
            parse_m23_instrumentation(instrument(final=0))

if __name__=='__main__': unittest.main()
