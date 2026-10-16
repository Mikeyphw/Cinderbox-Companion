"""M20 consolidated coverage: exact scenario matrix, safety and fail-closed host gates."""
import json
from pathlib import Path
import re
import sys
from unittest import TestCase
from unittest.mock import patch
from argparse import Namespace
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import m14_device_qualification as m14
import m20_qualification as m20

SRC=ROOT/'app/src/androidTest/java/com/sdvsync/qualification/M20ConsolidatedDeviceTest.kt'
FIX=ROOT/'app/src/androidTest/java/com/sdvsync/qualification/M20OwnedFixtures.kt'
MAINT=ROOT/'app/src/androidTest/java/com/sdvsync/qualification/M20FixtureMaintenanceDeviceTest.kt'
WORKER=ROOT/'app/src/debug/java/com/sdvsync/qualification/M20SyntheticWorkerService.kt'

class TestM20Campaign(TestCase):
    def test_exact_52_cases_and_eight_lanes(self):
        lanes=m20.matrix()
        self.assertEqual([len(lanes[k]['cases']) for k in 'ABCDEFGH'],[8,7,8,7,6,6,5,5])
        source=SRC.read_text()
        actual=set(re.findall(r'@Test fun ([a-h]\d{2}\w+)\(',source))
        expected=set(c for lane in lanes.values() for c in lane['cases'])
        self.assertEqual(actual,expected)
        self.assertEqual(len(actual),52)
        for letter,spec in lanes.items():
            self.assertTrue(spec['class'].endswith('DeviceTest'))
            self.assertEqual(spec['force_stop'],letter=='C')

    def test_manifest_is_static_and_no_empty_case(self):
        body=json.loads((HERE/'m20_scenarios.json').read_text())
        self.assertEqual(body['total'],52)
        self.assertEqual(set(body['lanes']),set('ABCDEFGH'))
        self.assertTrue(all(body['lanes'][k]['cases'] for k in 'ABCDEFGH'))

    def test_process_and_worker_are_unsafe_only_by_explicit_opt_in(self):
        body=(HERE/'m20_qualification.py').read_text()
        self.assertIn('force_stop_opt_in',body)
        self.assertIn("'C' not in selection or args.force_stop_opt_in",body)
        self.assertIn("device.shell('am','force-stop',m14.PACKAGE",body)
        self.assertIn("instrument(device,spec['class'],case,nonce,[case])",body)
        for fragment in ("device.shell('pm','clear'", "device.shell('pm','uninstall'",
                         "device.shell('reboot'",'device.instrument()'):
            self.assertNotIn(fragment,body)
        self.assertIn('m14.verify_artifacts(',body)
        self.assertIn('m14.verified_ci_checkout(',body)
        self.assertIn('m14.verify_ci(',body)

    def test_sandbox_canonicalization_marker_and_cleanup_fail_closed(self):
        fixture=FIX.read_text()
        for required in ('targetContext.filesDir.canonicalFile','m20-qualification-fixtures',
                         'm20-owned-', 'M20_FIXTURE_NOT_OWNED','M20_FIXTURE_UNEXPECTED_TOP_LEVEL_ENTRY',
                         'safeWalk(checked.work)','M20_CLEANUP_OWNERSHIP_UNVERIFIED',
                         'cleanupLegacyM19','M19_LEGACY_JOURNAL_UNVERIFIED',
                         'M20_INVENTORY_ROOT_UNTRUSTED','M20_NONCE_INVALID'):
            self.assertIn(required,fixture)
        self.assertNotIn('deleteRecursively()',fixture)
        self.assertIn('if (!retainOnSuccess) M20OwnedFixtures.cleanup(fixture)',fixture)
        self.assertIn('fun cleanupByOpaqueId(',fixture)
        self.assertIn('readText().split(\':\')',fixture)
        maint=MAINT.read_text()
        self.assertIn('m20_maintenance_opt_in',maint)
        self.assertNotIn('getExternalStorageDirectory',maint)

    def test_debug_worker_is_not_exported_or_network_connected(self):
        manifest=(ROOT/'app/src/debug/AndroidManifest.xml').read_text()
        self.assertIn('M20SyntheticWorkerService',manifest)
        self.assertIn('android:exported="false"',manifest)
        service=WORKER.read_text()
        self.assertIn('START_NOT_STICKY',service)
        self.assertIn('stopSelf(',service)
        self.assertIn('ownedWork(',service)
        self.assertIn('if (job?.isActive == true)',service)
        self.assertNotIn('http',service.lower())
        self.assertNotIn('SteamClientManager',service)

    def test_diagnostics_are_allowlisted(self):
        secret='token=PRIVATE /data/user/0/PRIVATE'
        raw=('INSTRUMENTATION_STATUS: test=c01CheckpointSurvivesNewObject\n'
             'INSTRUMENTATION_STATUS: stack=java.lang.SecurityException: '+secret+'\n'
             ' at com.sdvsync.qualification.M20CCrashDeviceTest'
             '(M20ConsolidatedDeviceTest.kt:211)\nINSTRUMENTATION_STATUS_CODE: -2\n')
        result=m20.diagnostic(raw,'c01CheckpointSurvivesNewObject')
        self.assertEqual(result,dict(category='ANDROID_SECURITY_RESTRICTION',source_line=211))
        self.assertNotIn('PRIVATE',repr(result))
        self.assertNotIn('/data/user',repr(result))
        self.assertNotIn('token=',repr(result))
        self.assertEqual(m20.diagnostic('INSTRUMENTATION_CODE: -1','other')['category'],
                         'INSTRUMENTATION_FAILED')

    def test_no_side_effects_without_opt_in(self):
        with tempfile.TemporaryDirectory() as temp:
            args=Namespace(repo=ROOT,run_id=1,transport='termux-root',all=True,
                           all_safe_lanes=False,lane=None,install=False,allow_replace=True,
                           ui_opt_in=True,test_profile_opt_in=True,force_stop_opt_in=True,
                           output=Path(temp)/'report.json')
            with patch.object(m14,'command') as command:
                self.assertEqual(1,m20.execute(args))
                command.assert_not_called()
            doc=json.loads(args.output.read_text())
            self.assertEqual(doc['failure_code'],'M20_INSTALL_EXPLICIT_CONSENT_REQUIRED')
            self.assertTrue(all(x['status']=='NOT_RUN' for x in doc['lanes'].values()))
            self.assertFalse(doc['release_qualified'])
            self.assertFalse(doc['publication_allowed'])

    def test_force_stop_refusal_precedes_git_and_install(self):
        with tempfile.TemporaryDirectory() as temp:
            args=Namespace(repo=ROOT,run_id=1,transport='termux-root',all=True,
                           all_safe_lanes=False,lane=None,install=True,allow_replace=True,
                           ui_opt_in=True,test_profile_opt_in=True,force_stop_opt_in=False,
                           output=Path(temp)/'report.json')
            with patch.object(m14,'command') as command:
                self.assertEqual(1,m20.execute(args))
                command.assert_not_called()
            self.assertEqual(json.loads(args.output.read_text())['failure_code'],
                             'M20_FORCE_STOP_CONSENT_REQUIRED')

    def test_parse_requires_full_method_accounting(self):
        spec=m20.matrix()['B']
        text=''.join('INSTRUMENTATION_STATUS: test='+name+'\nINSTRUMENTATION_STATUS_CODE: 0\n'
                     for name in spec['cases'])+'INSTRUMENTATION_CODE: -1\n'
        self.assertEqual(m14.parse_instrumentation(text,frozenset(spec['cases']))['status'],'PASS')
        with self.assertRaises(m14.DeviceGateError):
            m14.parse_instrumentation(text.replace('STATUS_CODE: 0','STATUS_CODE: -2',1),
                                      frozenset(spec['cases']))

    def test_ci_source_signing_and_one_apk_build(self):
        for file in ('build.yml','devtool-android-build.yml'):
            text=(ROOT/'.github/workflows'/file).read_text()
            self.assertIn(m20.CI_STEP,text)
            self.assertIn("-p 'test_m20_*.py'",text)
            self.assertEqual(text.count('M14 compile isolated Android instrumentation APK'),1)
            self.assertIn('m16_debug_signing.py verify',text)
        config=(ROOT/'.devtool.toml').read_text()
        self.assertIn('[wrapper.commands.m20-check]',config)
        self.assertIn('m20-check = ["job:m20-host"]',config)

    def test_merge_rejects_missing_lanes(self):
        with tempfile.TemporaryDirectory() as temp:
            base=m20.new_report(123,'termux-root',['A'])
            base.update(repository=m14.REPO,source_commit='a'*40,runner_source_commit='a'*40,
                        ci_checkout_commit='b'*40,ci_checkout_ref='refs/pull/1/merge',
                        apk_sha256='c'*64,test_apk_sha256='d'*64,
                        device={'api_level':36,'abi':'arm64-v8a'},ci='PASS',install='PASS',
                        overall='PASS_SELECTED_M20_LANES')
            base['lanes']['A'].update(status='PASS',cases={n:'PASS' for n in m20.matrix()['A']['cases']})
            paths=[Path(temp)/'a.json',Path(temp)/'b.json']
            for p in paths:p.write_text(json.dumps(base))
            args=Namespace(merge_reports=[str(x) for x in paths],output=Path(temp)/'merged.json')
            self.assertEqual(1,m20.merge(args))
            result=json.loads(args.output.read_text())
            self.assertEqual(result['failure_code'],'M20_MERGE_OVERLAPPING_LANES')

    def test_all_52_mocked_scenarios_execute_without_rerunning_old_milestones(self):
        class FakeDevice:
            def __init__(self):self.running=True;self.stops=0;self.invocations=[]
            def device_info(self):return {'api_level':36,'abi':'arm64-v8a'}
            def installed(self,pkg):return True
            def install(self,*a,**kw):return 'Success'
            def launch(self):self.running=True;return 'Status: ok\nActivity: com.sdvsync/.MainActivity\n'
            def shell(self,*parts,**kw):
                if parts[:2]==('sh','-c'):return '12345' if self.running else ''
                if parts[:2]==('am','force-stop'):
                    self.running=False;self.stops+=1;return ''
                if parts[:2]==('am','instrument'):
                    self.running=True
                    key=parts[parts.index('class')+1]
                    klass,_,method=key.partition('#')
                    lane=next(v for v in m20.matrix().values() if v['class']==klass)
                    tests=[method] if method else lane['cases']
                    self.invocations.extend(tests)
                    return ''.join('INSTRUMENTATION_STATUS: test='+x+'\nINSTRUMENTATION_STATUS_CODE: 0\n'
                                   for x in tests)+'INSTRUMENTATION_CODE: -1\n'
                raise AssertionError(parts)
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            args=Namespace(repo=ROOT,run_id=123,transport='termux-root',all=True,
                           all_safe_lanes=False,lane=None,install=True,allow_replace=True,
                           ui_opt_in=True,test_profile_opt_in=True,force_stop_opt_in=True,
                           output=td/'report.json')
            device=FakeDevice()
            gh_run={'head_branch':m20.BRANCH}
            def gh(args):
                return {'jobs':[{'steps':[{'name':m20.CI_STEP,'conclusion':'success'}]}]} if 'jobs?' in args[0] else gh_run
            def command(argv,**kw):
                if argv[0]=='git': return ''
                if argv[:3]==['gh','run','download']: return ''
                raise AssertionError(argv)
            from unittest.mock import patch
            with patch.object(m14,'git_head',return_value='a'*40), \
                 patch.object(m14,'command',side_effect=command), \
                 patch.object(m14,'json_from_gh',side_effect=gh), \
                 patch.object(m20,'verify_ci'), \
                 patch.object(m14,'read_json',return_value={'source_commit':'b'*40,'source_ref':'refs/pull/25/merge'}), \
                 patch.object(m14,'verified_ci_checkout',return_value=('b'*40,'refs/pull/25/merge')), \
                 patch.object(m14,'verify_artifacts',return_value=(td/'app.apk',td/'test.apk','c'*64,'d'*64)), \
                 patch.object(m14,'Transport',return_value=device):
                self.assertEqual(0,m20.execute(args))
            report=json.loads(args.output.read_text())
            self.assertEqual(report['overall'],m20.SUCCESS)
            self.assertEqual(device.stops,1)
            self.assertEqual(len(device.invocations),52)
            self.assertEqual(len(set(device.invocations)),52)
            self.assertEqual(report['process_gone'],'PASS')
            self.assertTrue(all(v['status']=='PASS' for v in report['lanes'].values()))
            self.assertFalse(report['m19_reexecuted'])

    def test_full_merge_produces_one_52_case_report(self):
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp)
            base=m20.new_report(123,'termux-root',[])
            base.update(repository=m14.REPO,source_commit='a'*40,runner_source_commit='a'*40,
                        ci_checkout_commit='b'*40,ci_checkout_ref='refs/pull/25/merge',
                        apk_sha256='c'*64,test_apk_sha256='d'*64,
                        device={'api_level':36,'abi':'arm64-v8a'},ci='PASS',install='PASS',
                        overall='PASS_SELECTED_M20_LANES')
            paths=[]
            for key,spec in m20.matrix().items():
                doc=json.loads(json.dumps(base));doc['lanes_requested']=[key]
                doc['lanes'][key].update(status='PASS',cases={c:'PASS' for c in spec['cases']})
                if key=='C':doc.update(force_stop='PASS',process_gone='PASS',cold_relaunch='PASS')
                path=temp/(key+'.json');path.write_text(json.dumps(doc));paths.append(str(path))
            output=temp/'consolidated.json'
            self.assertEqual(0,m20.merge(Namespace(merge_reports=paths,output=output)))
            result=json.loads(output.read_text())
            self.assertEqual(result['overall'],m20.SUCCESS)
            self.assertEqual(result['force_stop'],'PASS')
            self.assertEqual(result['process_gone'],'PASS')
            self.assertEqual(result['cold_relaunch'],'PASS')
            self.assertEqual(sum(sum(v=='PASS' for v in x['cases'].values()) for x in result['lanes'].values()),52)
            self.assertFalse(result['publication_allowed'])

    def test_evidence_always_non_release(self):
        report=m20.new_report(1,'termux-root',['A'])
        for key in ('device_qualified','release_qualified','publication_allowed',
                    'automatic_uninstall','automatic_data_clear','automatic_reboot',
                    'm14_reexecuted','m15_reexecuted','m17_reexecuted','m18_reexecuted','m19_reexecuted'):
            self.assertIs(report[key],False)

if __name__=='__main__':
    import unittest
    unittest.main()
