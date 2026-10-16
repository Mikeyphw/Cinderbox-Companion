"""M15 host gates; no Android installation and no network required."""
from pathlib import Path
from unittest.mock import patch
import json
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import m14_device_qualification as m14
import m15_device_qualification as m15


class M15QualificationTests(unittest.TestCase):
    def test_m15_case_list_matches_actual_device_methods(self):
        source = (HERE.parents[1] / 'app/src/androidTest/java/com/sdvsync/qualification/M15IntegratedDeviceTest.kt').read_text()
        import re
        methods = set(re.findall(r'@Test\s+fun\s+([A-Za-z][A-Za-z0-9_]*)\s*\(', source))
        self.assertEqual(m15.TESTS, methods)
        self.assertEqual(6, len(methods))
        self.assertIn('cacheDir.canonicalFile', source)
        self.assertIn('.m15-owned', source)
        self.assertNotIn('getExternalStorageDirectory', source)

    def test_only_all_m15_cases_and_final_runner_success_can_pass(self):
        sample = ''.join(f'INSTRUMENTATION_STATUS: test={name}\nINSTRUMENTATION_STATUS_CODE: 0\n'
                         for name in sorted(m15.TESTS)) + 'INSTRUMENTATION_CODE: -1\n'
        self.assertEqual('PASS', m14.parse_instrumentation(sample, m15.TESTS)['status'])
        for data in (sample.replace('INSTRUMENTATION_CODE: -1', 'INSTRUMENTATION_CODE: 0'),
                     sample.replace('INSTRUMENTATION_CODE: -1', ''),
                     sample.replace('INSTRUMENTATION_STATUS_CODE: 0', 'INSTRUMENTATION_STATUS_CODE: -2', 1),
                     sample.replace('INSTRUMENTATION_STATUS_CODE: 0', 'INSTRUMENTATION_STATUS_CODE: -1', 1),
                     sample.replace('INSTRUMENTATION_CODE: -1', 'INSTRUMENTATION_CODE: -1\nINSTRUMENTATION_CODE: -1'),
                     sample.replace(f'INSTRUMENTATION_STATUS: test={sorted(m15.TESTS)[0]}',
                                    'INSTRUMENTATION_STATUS: test=unknown')):
            with self.assertRaises(m14.DeviceGateError):
                m14.parse_instrumentation(data, m15.TESTS)

    def test_report_never_contains_junit_raw_output(self):
        selected = sorted(m15.TESTS)[0]
        raw = (f'INSTRUMENTATION_STATUS: test={selected}\nINSTRUMENTATION_STATUS_CODE: -2\n'
               'INSTRUMENTATION_STATUS: stack=/private/secret\nINSTRUMENTATION_CODE: -1\n')
        with self.assertRaises(m14.DeviceGateError) as err:
            m14.parse_instrumentation(raw, m15.TESTS)
        serialized = json.dumps(err.exception.case_summary)
        self.assertNotIn('secret', serialized)
        self.assertNotIn('stack', serialized)
        self.assertEqual('FAIL', err.exception.case_summary['cases'][selected])

    def test_m15_ci_rejects_missing_or_skipped_source_gate(self):
        branch = 'feature/m15-integrated-android-qualification'
        steps = ['M14 device qualification runner regressions',
                 'M14 compile isolated Android instrumentation APK',
                 'M14 upload isolated instrumentation APK', m15.M15_CI_STEP]
        jobs = {'jobs': [{'steps': [{'name': n, 'conclusion': 'success'} for n in steps]}]}
        with patch('m13_qualification.assess_ci', return_value={}):
            m15.verify_m15_ci({'head_branch': branch}, jobs, 'a'*40)
            for bad in ([], [n for n in steps if n != m15.M15_CI_STEP]):
                with self.assertRaises(m14.DeviceGateError):
                    m15.verify_m15_ci({'head_branch': branch},
                                      {'jobs': [{'steps': [{'name': n, 'conclusion': 'success'} for n in bad]}]}, 'a'*40)
            with self.assertRaises(m14.DeviceGateError):
                m15.verify_m15_ci({'head_branch': 'feature/m14-postmerge-device-provenance'}, jobs, 'a'*40)

    def test_no_opt_in_fails_before_network_or_install_and_stays_unqualified(self):
        from argparse import Namespace
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'result.json'
            args = Namespace(install=False, repo=Path(directory), run_id=1, ci_head=None,
                             transport='termux-root', output=report, allow_replace=False)
            with patch.object(m14, 'command') as command:
                self.assertEqual(1, m15.run(args))
                command.assert_not_called()
            result = json.loads(report.read_text())
            self.assertEqual('INSTALL_REQUIRES_EXPLICIT_FLAG', result['failure_code'])
            self.assertEqual('NOT_RUN', result['instrumentation'])
            for key in ('release_qualified', 'publication_allowed', 'device_qualified',
                        'automatic_device_install', 'automatic_uninstall', 'm14_reexecuted'):
                self.assertIs(result[key], False)

    def test_runner_only_targets_m15_class_and_no_uninstall_path(self):
        src = (HERE/'m15_device_qualification.py').read_text()
        self.assertIn('device.instrument(test_class=CLASS)', src)
        self.assertNotIn('device.instrument()', src)
        self.assertNotIn("'pm','uninstall'", src)
        self.assertNotIn('shutil.rmtree', src)
        workflow = (HERE.parents[1]/'.github/workflows/build.yml').read_text()
        self.assertIn('M15 integrated Android qualification regressions', workflow)
        self.assertIn("-p 'test_m15_*.py'", workflow)
        self.assertEqual(1, workflow.count('M14 compile isolated Android instrumentation APK'))


if __name__ == '__main__':
    unittest.main()
