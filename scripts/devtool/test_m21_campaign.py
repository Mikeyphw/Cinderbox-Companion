"""M21 source-bound fail-closed acceptance and release candidate regression contracts."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from argparse import Namespace
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import m14_device_qualification as m14
import m21_campaign as m21

class M21HostTests(unittest.TestCase):
    def test_manifest_exact_unique_scenario_ids(self):
        d=m21.matrix()
        self.assertEqual([len(d[k]['cases']) for k in 'UTIR'],[4,4,6,4])
        self.assertEqual(sum(len(x['cases']) for x in d.values()),18)
        self.assertTrue(set('UTI')=={k for k,v in d.items() if v['class']})
        self.assertEqual(json.loads((HERE/'m21_scenarios.json').read_text())
                         ['historical_android_passes_not_reexecuted'],74)

    def test_device_methods_exist_and_are_read_only_or_namespaced(self):
        source=(ROOT/'app/src/androidTest/java/com/sdvsync/qualification/M21ReadinessDeviceTest.kt').read_text()
        methods=set(re.findall(r'@Test\s+fun\s+([uti][0-9]{2}\w+)\(',source))
        expected={n for k in 'UTI' for n in m21.matrix()[k]['cases']}
        self.assertEqual(methods,expected)
        for content in ['createAndroidComposeRule<MainActivity>()',
                        'SteamSessionStore','SteamCloudService','InstallationScanner',
                        'm21-upgrade-owned-', 'm21_auth_opt_in']:
            self.assertIn(content,source)
        for forbidden in ('SteamAuthenticator.logout(', 'SteamAuthenticator.login(',
                          'uploadSave(', 'downloadSave(', 'deleteRecursively(',
                          'pm clear','pm uninstall','getExternalStorageDirectory'):
            self.assertNotIn(forbidden,source)

    def test_android_compose_node_assertions_are_member_calls(self):
        """Guard the M21 AndroidTest compile failure seen in CI #38940534401."""
        src=(ROOT/'app/src/androidTest/java/com/sdvsync/qualification/M21ReadinessDeviceTest.kt').read_text()
        self.assertNotIn("import androidx.compose.ui.test.assertExists",src)
        self.assertIn(".assertExists()",src)
        self.assertIn("import androidx.compose.ui.test.junit4.createAndroidComposeRule",src)

    def test_cloud_diagnostics_never_log_names_or_payload(self):
        src=(ROOT/'app/src/main/java/com/sdvsync/steam/SteamCloudService.kt').read_text()
        self.assertNotIn('first50=',src)
        self.assertNotIn('filename=',src)
        self.assertNotIn('batchId=$batchId',src)
        self.assertNotIn('committed $fullPath',src)
        for match in re.findall(r'AppLogger\.d\((?:[\s\S]*?)\)',src):
            self.assertNotIn('$fullPath',match)
        self.assertIn('metadata received',src)

    def test_ci_and_devtool_one_build(self):
        for workflow in ['build.yml','devtool-android-build.yml']:
            w=(ROOT/'.github/workflows'/workflow).read_text()
            self.assertIn(m21.CI_STEP,w)
            self.assertIn("-p 'test_m21_*.py'",w)
            self.assertEqual(w.count('M14 compile isolated Android instrumentation APK'),1)
            self.assertIn('M16 verify pinned instrumentation APK signer',w)
        cfg=(ROOT/'.devtool.toml').read_text()
        self.assertIn('[wrapper.commands.m21-check]',cfg)
        self.assertIn('[targets.cinderbox.jobs.m21-host]',cfg)
        self.assertIn('m21-check = ["job:m21-host"]',cfg)
        base=(ROOT/'scripts/devtool/m14_device_qualification.py').read_text()
        self.assertGreaterEqual(base.count(m21.BRANCH),2)

    def test_release_identity_requires_distinct_pin_even_with_matching_digest(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'candidate.apk'
            p.write_bytes(b'synthetic-test-content')
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            with self.assertRaises(m14.DeviceGateError) as ctx:
                m21.verify_release_apk(p,digest,'a'*64,'a'*64)
            self.assertEqual(ctx.exception.code,'M21_RELEASE_REUSES_DEBUG_KEY')
            with self.assertRaises(m14.DeviceGateError) as ctx:
                m21.verify_release_apk(p,'0'*64,'a'*64,'b'*64)
            self.assertEqual(ctx.exception.code,'M21_RELEASE_DIGEST_MISMATCH')

    def test_release_requires_real_apksigner_aapt_and_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'candidate.apk'
            p.write_bytes(b'synthetic-test-content')
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            signer='Signer #1 certificate SHA-256 digest: '+'a'*64+'\n'
            with patch.object(m21.shutil,'which',return_value='/opt/aapt'),\
                 patch.object(m21,'run_command',side_effect=[signer,"package: name='com.sdvsync' versionCode='14' versionName='0.1.1'\n"]):
                result=m21.verify_release_apk(p,digest,'a'*64,'b'*64)
            self.assertEqual(set(result),set(m21.matrix()['R']['cases']))
            self.assertTrue(all(v=='PASS' for v in result.values()))
            with patch.object(m21.shutil,'which',return_value='/opt/aapt'),\
                 patch.object(m21,'run_command',side_effect=[signer,"package: name='com.sdvsync' versionCode='14'\napplication-debuggable\n"]):
                with self.assertRaises(m14.DeviceGateError) as ctx:
                    m21.verify_release_apk(p,digest,'a'*64,'b'*64)
                self.assertEqual(ctx.exception.code,'M21_RELEASE_PACKAGE_OR_DEBUGGABLE')

    def args(self,td,**kw):
        base=dict(repo=ROOT,run_id=123,transport='termux-root',lane='U',
                  ui_opt_in=True,signed_out_opt_in=True,authenticated_opt_in=False,
                  installation_check_opt_in=False,upgrade_opt_in=False,
                  install=True,allow_replace=True,output=Path(td)/'report.json')
        base.update(kw)
        return Namespace(**base)

    def test_opt_in_gates_precede_any_external_device_or_github_call(self):
        for fields,code in [({'ui_opt_in':False},'M21_INSTALL_AND_UI_CONSENT_REQUIRED'),
                            ({'allow_replace':False},'M21_INSTALL_AND_UI_CONSENT_REQUIRED'),
                            ({'signed_out_opt_in':False},'M21_OFFLINE_PROFILE_CONSENT_REQUIRED'),
                            ({'lane':'T'},'M21_AUTHENTICATED_READ_ONLY_CONSENT_REQUIRED'),
                            ({'lane':'I'},'M21_INSTALLATION_AND_UPGRADE_CONSENT_REQUIRED')]:
            with self.subTest(fields=fields),tempfile.TemporaryDirectory() as td:
                with patch.object(m14,'command') as command:
                    result=m21.run_device(self.args(td,**fields))
                    command.assert_not_called()
                self.assertEqual(result,1)
                doc=json.loads((Path(td)/'report.json').read_text())
                self.assertEqual(doc['failure_code'],code)
                self.assertFalse(doc['release_qualified'])
                self.assertFalse(doc['publication_allowed'])
                self.assertTrue(doc['historical_74_tests_reexecuted'] is False)

    def test_failure_diagnostics_do_not_emit_stack_or_secret(self):
        text='INSTRUMENTATION_STATUS: test=t04SteamCloudMetadataReadOnlyRequest\nINSTRUMENTATION_STATUS: stack=java.lang.AssertionError: /private/path /user/name\nINSTRUMENTATION_STATUS_CODE: -2\n'
        self.assertEqual(m21.classify(text,'t04SteamCloudMetadataReadOnlyRequest'),
                         {'category':'ASSERTION_OR_DEVICE_REJECTION'})
        self.assertNotIn('/private/path',repr(m21.classify(text,'t04SteamCloudMetadataReadOnlyRequest')))

    def test_merge_rejects_source_change_and_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); reports=[]
            for lane in 'UTIR':
                d=m21.info_report(123,'termux-root' if lane!='R' else None,[lane])
                d.update(ci='PASS',install='PASS' if lane!='R' else 'NOT_RUN',
                         repository=m21.REPO,source_commit='a'*40,runner_source_commit='a'*40,
                         ci_checkout_commit='b'*40,ci_checkout_ref='refs/pull/42/merge',
                         apk_sha256='c'*64,test_apk_sha256='d'*64,
                         overall='PASS_SELECTED_M21_LANES',
                         device={'api_level':36,'abi':'arm64-v8a'} if lane!='R' else None)
                d['lanes'][lane]['status']='PASS'
                d['lanes'][lane]['cases']={n:'PASS' for n in m21.matrix()[lane]['cases']}
                path=root/f'{lane}.json';path.write_text(json.dumps(d));reports.append(path)
            report_args=Namespace(merge_reports=[str(p) for p in reports], output=root/'merged.json')
            self.assertEqual(m21.merge(report_args),0)
            doc=json.loads(report_args.output.read_text())
            self.assertEqual(doc['overall'],m21.SUCCESS)
            self.assertFalse(doc['publication_allowed'])
            self.assertFalse(doc['release_qualified'])
            report_args.merge_reports=[str(reports[0])]*2+[str(reports[1])]
            self.assertEqual(m21.merge(report_args),1)
            report_args.merge_reports=[str(p) for p in reports]
            tampered=json.loads(reports[1].read_text());tampered['source_commit']='e'*40
            reports[1].write_text(json.dumps(tampered))
            self.assertEqual(m21.merge(report_args),1)
            self.assertEqual(json.loads(report_args.output.read_text())['failure_code'],
                             'M21_MERGE_SOURCE_OR_STATUS_MISMATCH')

    def test_read_only_release_gate_never_signs_or_publishes(self):
        code=(HERE/'m21_campaign.py').read_text()
        self.assertNotIn('gh release create',code)
        self.assertNotIn('pm clear',code)
        self.assertNotIn('uninstall(',code)
        self.assertNotIn('loginWith',code)
        self.assertIn("report['release_qualified']=False",code)

if __name__=='__main__': unittest.main()
