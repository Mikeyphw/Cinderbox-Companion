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

    def test_pr_merge_commit_is_bound_to_head_base_ref_and_parents(self):
        from unittest.mock import patch
        head='b'*40; base='a'*40; merge='c'*40
        record={'event':'pull_request','head_sha':head,
                'head_branch':'feature/m14-isolated-device-qualification',
                'pull_requests':[{'number':18,'head':{'sha':head,'ref':'feature/m14-isolated-device-qualification'},
                                  'base':{'sha':base}}]}
        pr={'number':18,'head':{'sha':head,'ref':record['head_branch']},
            'base':{'sha':base},'merge_commit_sha':merge,'state':'open'}
        git_ref={'ref':'refs/pull/18/merge','object':{'sha':merge}}
        commit={'sha':merge,'parents':[{'sha':base},{'sha':head}]}
        with patch.object(m14,'json_from_gh',side_effect=[pr,git_ref,commit]) as f:
            self.assertEqual((merge,'refs/pull/18/merge'), m14.verified_ci_checkout(record,head))
            self.assertEqual(3,f.call_count)
        wrong_parents={'sha':merge,'parents':[{'sha':head},{'sha':base}]}
        with patch.object(m14,'json_from_gh',side_effect=[pr,git_ref,wrong_parents]):
            with self.assertRaisesRegex(m14.DeviceGateError,'PR_MERGE_PARENTS_MISMATCH'):
                m14.verified_ci_checkout(record,head)
        with patch.object(m14,'json_from_gh',side_effect=[pr,
                {'ref':'refs/pull/18/merge','object':{'sha':'d'*40}},commit]):
            with self.assertRaisesRegex(m14.DeviceGateError,'PR_MERGE_REF_MISMATCH'):
                m14.verified_ci_checkout(record,head)
        with patch.object(m14,'json_from_gh',side_effect=[{**pr,'head':{'sha':'d'*40}},git_ref,commit]):
            with self.assertRaisesRegex(m14.DeviceGateError,'PR_CHANGED_SINCE_CI'):
                m14.verified_ci_checkout(record,head)
        with patch.object(m14,'json_from_gh') as f:
            with self.assertRaisesRegex(m14.DeviceGateError,'CI_HEAD_MISMATCH'):
                m14.verified_ci_checkout(record,'d'*40)
            f.assert_not_called()

    def test_push_checkout_needs_exact_branch_identity(self):
        from unittest.mock import patch
        head='b'*40
        with patch.object(m14,'json_from_gh') as f:
            self.assertEqual((head,'refs/heads/master'),m14.verified_ci_checkout(
                {'event':'push','head_sha':head,'head_branch':'master'},head))
            with self.assertRaisesRegex(m14.DeviceGateError,'UNEXPECTED_PUSH_BRANCH'):
                m14.verified_ci_checkout({'event':'push','head_sha':head,'head_branch':'unknown'},head)
            f.assert_not_called()

    def test_pr_merge_evidence_must_match_ci_checkout_and_run(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);main=root/'debug';tests=root/'test';main.mkdir();tests.mkdir()
            a=main/'debug.apk';b=tests/'test.apk'
            for path in (a,b):
                with zipfile.ZipFile(path,'w') as z:
                    z.writestr('AndroidManifest.xml',b'x'*4096)
                    z.writestr('classes.dex',b'Y'*300)
            digest=m14.sha256(a);head='b'*40; merge='c'*40
            prov={'repository':m14.REPO,'source_commit':merge,
                  'source_ref':'refs/pull/18/merge','github_run_id':'38794689936',
                  'variant':'debug','format':'apk','qualified_release':False,
                  'publication_allowed':False,'apk':{'filename':'debug.apk','size_bytes':a.stat().st_size,
                  'sha256':digest,'package_name':m14.PACKAGE,
                  'signature_verified':True,'debug_signed':True}}
            qual={'producer':'cinderbox-m13','source_commit':merge,'source_contract':'PASS',
                  'apk_integrity':'PASS_SHA256_MATCHES_M3','artifact_sha256':digest,
                  'release_qualified':False,'publication_allowed':False}
            (main/'M3_PROVENANCE.json').write_text(json.dumps(prov))
            (main/'M13_QUALIFICATION.json').write_text(json.dumps(qual))
            self.assertEqual(digest,m14.verify_artifacts(main,tests,merge,
                source_ref='refs/pull/18/merge',run_id=38794689936)[2])
            for changes in ({'source_commit':head},{'source_ref':'refs/heads/master'},
                            {'github_run_id':'38787031168'}):
                tampered={**prov,**changes}
                (main/'M3_PROVENANCE.json').write_text(json.dumps(tampered))
                with self.assertRaises(m14.DeviceGateError):
                    m14.verify_artifacts(main,tests,merge,source_ref='refs/pull/18/merge',
                                         run_id=38794689936)
            (main/'M3_PROVENANCE.json').write_text(json.dumps(prov))
            with a.open('ab') as f:f.write(b'tampered')
            with self.assertRaises(m14.DeviceGateError):
                m14.verify_artifacts(main,tests,merge,source_ref='refs/pull/18/merge',
                                     run_id=38794689936)

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

    def test_merged_pr_without_run_association_checks_immutable_ci_parents(self):
        from unittest.mock import patch
        head='7'*40; base='4'*40; checkout='b'*40
        created='2026-10-15T20:33:00Z'; merged='2026-10-15T20:39:26Z'
        run={'event':'pull_request','head_sha':head,'head_branch':'feature/m14-isolated-device-qualification',
             'pull_requests':[],'created_at':created}
        association={'number':18,'head':{'sha':head,'ref':run['head_branch']},
                     'base':{'sha':base},'merged_at':merged}
        pr={**association,'state':'closed','merge_commit_sha':'a'*40}
        commit={'sha':checkout,'parents':[{'sha':base},{'sha':head}]}
        with patch.object(m14,'list_from_gh',return_value=[association]) as assoc, \
             patch.object(m14,'json_from_gh',side_effect=[pr,commit]) as api:
            self.assertEqual((checkout,'refs/pull/18/merge'),
                m14.verified_ci_checkout(run,head,artifact_commit=checkout,
                                         artifact_ref='refs/pull/18/merge'))
            self.assertEqual(2,api.call_count)  # No deleted PR merge ref lookup
            assoc.assert_called_once()
            self.assertIn('/commits/'+head+'/pulls',assoc.call_args.args[0][0])

    def test_merged_pr_provenance_negative_cases_fail_closed(self):
        from unittest.mock import patch
        h='7'*40;b='4'*40;c='b'*40
        merged='2026-10-15T20:39:26Z'
        run={'event':'pull_request','head_sha':h,'head_branch':'feature/m14-isolated-device-qualification',
             'pull_requests':[],'created_at':'2026-10-15T20:33:00Z'}
        assoc={'number':18,'head':{'sha':h,'ref':run['head_branch']},'base':{'sha':b},'merged_at':merged}
        pr={**assoc,'state':'closed','merge_commit_sha':'a'*40}
        for linked in ([],[assoc,assoc], [{**assoc,'head':{'sha':'0'*40,'ref':run['head_branch']}}]):
            with patch.object(m14,'list_from_gh',return_value=linked), \
                 patch.object(m14,'json_from_gh') as api:
                with self.assertRaisesRegex(m14.DeviceGateError,'PR_ASSOCIATION_AMBIGUOUS'):
                    m14.verified_ci_checkout(run,h,artifact_commit=c,artifact_ref='refs/pull/18/merge')
                api.assert_not_called()
        for sha,ref,commit in ((c,'refs/heads/master',{'sha':c,'parents':[{'sha':b},{'sha':h}]}),
                               ('d'*40,'refs/pull/18/merge',{'sha':c,'parents':[{'sha':b},{'sha':h}]}),
                               (c,'refs/pull/18/merge',{'sha':c,'parents':[{'sha':h},{'sha':b}]})):
            with patch.object(m14,'list_from_gh',return_value=[assoc]), \
                 patch.object(m14,'json_from_gh',side_effect=[pr,commit]):
                with self.assertRaises(m14.DeviceGateError):
                    m14.verified_ci_checkout(run,h,artifact_commit=sha,artifact_ref=ref)
        with patch.object(m14,'list_from_gh',return_value=[assoc]), \
             patch.object(m14,'json_from_gh',return_value=pr):
            with self.assertRaisesRegex(m14.DeviceGateError,'PR_TIMELINE_UNVERIFIABLE'):
                m14.verified_ci_checkout({**run,'created_at':'2026-10-16T01:00:00Z'},h,
                    artifact_commit=c,artifact_ref='refs/pull/18/merge')

    def test_historic_run_requires_explicit_ci_head_override(self):
        source=MODULE.read_text()
        self.assertIn("head=args.ci_head or local_head",source)
        self.assertIn("report['runner_source_commit']=local_head",source)
        self.assertIn("--ci-head",source)
        self.assertIn("run_data,head,artifact_commit=provenance.get('source_commit')",source)
        self.assertIn('verify_artifacts(\n                main,test,ci_commit,source_ref=ci_ref,run_id=args.run_id)',source)
        self.assertNotIn('pm uninstall',source)
        self.assertNotIn('pm clear',source)

if __name__=='__main__':unittest.main()
