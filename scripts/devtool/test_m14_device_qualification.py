"""Pure host regressions: M14 never equates installation with production qualification."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

MODULE = Path(__file__).with_name('m14_device_qualification.py')
spec = importlib.util.spec_from_file_location('m14_device_qualification',MODULE)
m14 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m14)
ROOT=Path(__file__).resolve().parents[2]

class M14HostQualification(unittest.TestCase):
    def test_instrumentation_must_finish_all_eight_real_cases(self):
        sample=''.join(f'INSTRUMENTATION_STATUS: test={name}\nINSTRUMENTATION_STATUS_CODE: 0\n'
                       for name in sorted(m14.TESTS))+'INSTRUMENTATION_CODE: -1\n'
        result=m14.parse_instrumentation(sample)
        self.assertEqual(8,result['completed'])
        self.assertEqual('PASS',result['status'])
        with self.assertRaises(m14.DeviceGateError):
            m14.parse_instrumentation(sample.replace('INSTRUMENTATION_CODE: -1','INSTRUMENTATION_CODE: 0'))
        with self.assertRaises(m14.DeviceGateError):
            m14.parse_instrumentation(sample.replace(next(iter(m14.TESTS)),'unknownCase'))
        with self.assertRaises(m14.DeviceGateError):
            m14.parse_instrumentation(sample+'INSTRUMENTATION_STATUS_CODE: -2\n')

    def test_ci_gate_rejects_nonfinal_or_missing_m14_checks(self):
        from unittest.mock import patch
        sha='a'*40
        base={'head_branch':'feature/m14-isolated-device-qualification'}
        jobs={'jobs':[{'steps':[{'name':n,'conclusion':'success'} for n in (
            'M14 device qualification runner regressions',
            'M14 compile isolated Android instrumentation APK',
            'M14 upload isolated instrumentation APK')]}]}
        with patch('m13_qualification.assess_ci',return_value={}):
            m14.verify_ci(base,jobs,sha)
            with self.assertRaises(m14.DeviceGateError):
                m14.verify_ci(base,{'jobs':[{'steps':[]}]},sha)

    def test_artifact_hash_identity_and_tamper_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work); main=root/'debug'; tests=root/'test';main.mkdir();tests.mkdir()
            a=main/'debug.apk'; b=tests/'test.apk'
            for path in (a,b):
                with zipfile.ZipFile(path,'w') as z:
                    z.writestr('AndroidManifest.xml',b'x'*4096)
                    z.writestr('classes.dex',b'Y'*300)
            sha=m14.sha256(a);commit='a'*40
            prov={'repository':m14.REPO,'source_commit':commit,'variant':'debug','format':'apk',
                  'qualified_release':False,'publication_allowed':False,
                  'apk':{'filename':'debug.apk','size_bytes':a.stat().st_size,
                         'sha256':sha,'package_name':m14.PACKAGE,
                         'signature_verified':True,'debug_signed':True}}
            qual={'producer':'cinderbox-m13','source_commit':commit,'source_contract':'PASS',
                  'apk_integrity':'PASS_SHA256_MATCHES_M3','artifact_sha256':sha,
                  'release_qualified':False,'publication_allowed':False}
            (main/'M3_PROVENANCE.json').write_text(json.dumps(prov))
            (main/'M13_QUALIFICATION.json').write_text(json.dumps(qual))
            self.assertEqual(sha,m14.verify_artifacts(main,tests,commit)[2])
            with a.open('ab') as f:f.write(b'bytes changed after evidence')
            with self.assertRaises(m14.DeviceGateError):
                m14.verify_artifacts(main,tests,commit)

    def test_explicit_install_and_existing_install_guard_are_part_of_runner(self):
        script=MODULE.read_text()
        self.assertIn("require(args.install,'INSTALL_REQUIRES_EXPLICIT_FLAG')",script)
        self.assertIn('EXISTING_INSTALL_REQUIRES_ALLOW_REPLACE',script)
        self.assertIn("if self.kind=='adb':",script)
        self.assertNotIn('pm uninstall',script)
        self.assertNotIn('pm clear',script)
        self.assertNotIn('force-stop',script)
        self.assertIn("'automatic_device_install':False",script)
        self.assertIn("'publication_allowed':False",script)

    def test_isolated_android_fixture_contract(self):
        source=(ROOT/'app/src/androidTest/java/com/sdvsync/qualification/M14IsolatedDeviceTest.kt').read_text()
        self.assertIn('targetContext.cacheDir',source)
        self.assertIn('createTempDirectory',source)
        self.assertIn('.m14-test-owned',source)
        self.assertIn('ModProfileTransaction(privateDir, mods).recover()',source)
        self.assertIn('GameDownloadRecovery(privateDir)',source)
        self.assertIn('ModBatchTransaction(privateDir, mods)',source)
        self.assertIn('SaveRestoreTransaction(privateDir)',source)
        for forbidden in ('SDV_SAVE_PATH', 'CINDERBOX_SAVE_PATH', 'CinderboxPaths.MODS_DIR',
                          'context.filesDir', 'su -c', 'SteamAuthenticator', 'deleteDatabase('):
            self.assertNotIn(forbidden,source)
        self.assertEqual(8,source.count('@Test fun '))

    def test_workflow_builds_and_uploads_tests_separate_from_debug_apk(self):
        for path in ('.github/workflows/build.yml','.github/workflows/devtool-android-build.yml'):
            workflow=(ROOT/path).read_text()
            self.assertIn("test_m14_*.py",workflow)
            self.assertIn('assembleDebugAndroidTest',workflow)
            self.assertIn('m14-androidtest-apk',workflow)
            self.assertNotIn('connectedDebugAndroidTest',workflow)

    def test_machine_report_excludes_serial_and_raw_results(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.json'
            m14.write_report(p,{'schema_version':1,'device':{'api_level':36,'abi':'arm64-v8a'},
                                 'overall':'FAILED_OR_BLOCKED','failure_code':'COMMAND_FAILED'})
            text=p.read_text()
            self.assertNotIn('serial',text)
            self.assertNotIn('stdout',text)
            self.assertEqual('COMMAND_FAILED',json.loads(text)['failure_code'])

if __name__=='__main__':unittest.main()
