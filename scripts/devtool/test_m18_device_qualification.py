"""M18 host gates: source, explicit consent, instrumentation, and process lifecycle."""
from argparse import Namespace
import json
from pathlib import Path
from unittest.mock import patch
import sys
import tempfile
import unittest

from ci_workflow_contract import effective_ci_source
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import m14_device_qualification as m14
import m18_device_qualification as m18

class FakeDevice:
    def __init__(self):
        self.running=False
        self.stopped=False
        self.commands=[]
    def shell(self,*a,**kw):
        self.commands.append(a)
        if a[:2]==('sh','-c'):
            return '1234' if self.running else ''
        if a[:2]==('am','force-stop'):
            self.running=False
            self.stopped=True
            return ''
        if a[:2]==('am','instrument'):
            if not self.running:
                # Android's instrumentation itself launches the app under test.
                self.running=True
            cls=a[a.index('class')+1].split('#')[-1]
            return 'INSTRUMENTATION_STATUS: test='+cls+'\nINSTRUMENTATION_STATUS_CODE: 0\nINSTRUMENTATION_CODE: -1\n'
        raise AssertionError(f'unexpected shell: {a}')
    def launch(self):
        self.running=True
        return 'Starting: Intent {}\nStatus: ok\nLaunchState: COLD\nActivity: com.sdvsync/.MainActivity\nComplete\n'
    def installed(self,pkg):
        return True
    def install(self,*a,**kw):
        return 'Success'
    def device_info(self):
        return {'api_level':36,'abi':'arm64-v8a'}

class M18HostTests(unittest.TestCase):
    def args(self,root,**changes):
        defaults=dict(repo=ROOT,run_id=123,ci_head='a'*40,transport='termux-root',
            force_stop_opt_in=True,ui_opt_in=True,test_profile_opt_in=True,
            install=True,allow_replace=True,output=Path(root)/'report.json')
        defaults.update(changes)
        return Namespace(**defaults)

    def test_exact_only_m18_methods_and_private_marker(self):
        src=(ROOT/'app/src/androidTest/java/com/sdvsync/qualification/M18ProcessRecoveryDeviceTest.kt').read_text()
        import re
        names=set(re.findall(r'@Test\s+fun\s+(\w+)\(',src))
        self.assertEqual(names,m18.TESTS)
        self.assertEqual(len(names),2)
        for term in ('createAndroidComposeRule<MainActivity>()',
                     'Continue offline','cinderbox_m18_test_only',
                     'edit().remove(key).commit()', 'M18_PREPARED'):
            self.assertIn(term,src)
        for forbidden in ('pm clear','pm uninstall','deleteRecursively','getExternalStorageDirectory',
                          'SteamAuthenticator.logout','System.exit','forceStopPackage','android.os.Process.killProcess'):
            self.assertNotIn(forbidden,src)

    def test_ci_and_config_are_source_bound(self):
        for flow in ('build.yml','devtool-android-build.yml'):
            wf=effective_ci_source(ROOT,'.github/workflows/'+flow)
            self.assertIn(m18.CI_STEP,wf)
            self.assertIn("-p 'test_m18_*.py'",wf)
            self.assertEqual(wf.count('M14 compile isolated Android instrumentation APK'),1)
            self.assertIn('m16_debug_signing.py verify',wf)
        conf=(ROOT/'.devtool.toml').read_text()
        self.assertIn('[wrapper.commands.m18-check]',conf)
        self.assertIn('m18-check = ["job:m18-host"]',conf)
        source=(ROOT/'scripts/devtool/m14_device_qualification.py').read_text()
        self.assertGreaterEqual(source.count('feature/m18-process-death-recovery'),2)

    def test_opt_in_denials_before_external_commands(self):
        scenarios=[('force_stop_opt_in','FORCE_STOP_REQUIRES_EXPLICIT_FLAG'),
                   ('ui_opt_in','LIVE_UI_REQUIRES_EXPLICIT_FLAG'),
                   ('test_profile_opt_in','ISOLATED_TEST_PROFILE_REQUIRES_EXPLICIT_FLAG'),
                   ('install','INSTALL_AND_REPLACE_REQUIRE_EXPLICIT_FLAGS'),
                   ('allow_replace','INSTALL_AND_REPLACE_REQUIRE_EXPLICIT_FLAGS')]
        for key,expected in scenarios:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as td:
                args=self.args(td,**{key:False})
                with patch.object(m14,'command') as cmd:
                    self.assertEqual(m18.run(args),1)
                    cmd.assert_not_called()
                result=json.loads(args.output.read_text())
                self.assertEqual(result['failure_code'],expected)
                self.assertEqual(result['force_stop'],'NOT_RUN')
                self.assertEqual(result['install'],'NOT_RUN')
                self.assertFalse(result['release_qualified'])
                self.assertFalse(result['publication_allowed'])

    def test_instrumentation_failure_is_fail_closed(self):
        for s in ['INSTRUMENTATION_STATUS: test='+m18.PREPARE+'\nINSTRUMENTATION_STATUS_CODE: -2\nINSTRUMENTATION_CODE: -1\n',
                  'INSTRUMENTATION_STATUS: test='+m18.PREPARE+'\nINSTRUMENTATION_STATUS_CODE: 0\n',
                  'INSTRUMENTATION_CODE: -1\n']:
            with self.subTest(s=s):
                with self.assertRaises(m14.DeviceGateError):
                    m14.parse_instrumentation(s,{m18.PREPARE})

    def test_missing_process_or_invalid_launch_blocks(self):
        with self.assertRaises(m14.DeviceGateError):
            m18.assert_launch('Status: ok\nActivity: some.other.Activity')
        with self.assertRaises(m14.DeviceGateError):
            m18.assert_launch('Status: fail\nActivity: com.sdvsync/.MainActivity')
        m18.assert_launch('Status: ok\nActivity: com.sdvsync/.MainActivity\n')
        class Bad:
            def shell(self,*args,**kwargs): return 'unexpected response'
        with self.assertRaises(m14.DeviceGateError): m18.pid_of(Bad())
        class Stopped:
            def shell(self,*args,**kwargs): return ''
        self.assertFalse(m18.pid_of(Stopped()))

    def test_ci_requires_m18_gate(self):
        names=['M14 device qualification runner regressions',
               'M14 compile isolated Android instrumentation APK',
               'M14 upload isolated instrumentation APK',m18.CI_STEP]
        jobs=lambda seq:{'jobs':[{'steps':[{'name':x,'conclusion':'success'} for x in seq]}]}
        with patch('m13_qualification.assess_ci',return_value={}):
            m18.verify_ci({'head_branch':'feature/m18-process-death-recovery'},jobs(names),'a'*40)
            with self.assertRaises(m14.DeviceGateError):
                m18.verify_ci({'head_branch':'feature/m18-process-death-recovery'},jobs(names[:-1]),'a'*40)
            with self.assertRaises(m14.DeviceGateError):
                m18.verify_ci({'head_branch':'feature/m17-android-ui-lifecycle'},jobs(names),'a'*40)

    def test_full_mocked_flow_real_force_stop_between_two_stages(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            args=self.args(td)
            dev=FakeDevice()
            provenance={'source_commit':'b'*40,'source_ref':'refs/pull/23/merge'}
            metadata={'head_branch':'feature/m18-process-death-recovery'}
            def gh(args):
                if args[0].endswith('jobs?per_page=100'):
                    return {'jobs':[{'steps':[{'name':m18.CI_STEP,'conclusion':'success'}]}]}
                return metadata
            def fake_command(argv,**kw):
                if argv[:2]==['git','-C']:
                    return ''
                if argv[:3]==['gh','run','download']:
                    return ''
                raise AssertionError(argv)
            with patch.object(m14,'git_head',return_value='a'*40),\
                 patch.object(m14,'command',side_effect=fake_command),\
                 patch.object(m14,'json_from_gh',side_effect=gh),\
                 patch.object(m18,'verify_ci'),\
                 patch.object(m14,'read_json',return_value=provenance),\
                 patch.object(m14,'verified_ci_checkout',return_value=('b'*40,'refs/pull/23/merge')),\
                 patch.object(m14,'verify_artifacts',return_value=(td/'a.apk',td/'t.apk','c'*64,'d'*64)),\
                 patch.object(m14,'Transport',return_value=dev):
                self.assertEqual(m18.run(args),0)
            report=json.loads(args.output.read_text())
            self.assertEqual(report['overall'],'PASS_REAL_PROCESS_RECOVERY_AUTOMATION')
            self.assertEqual(report['force_stop'],'PASS')
            self.assertEqual(report['process_gone'],'PASS')
            self.assertEqual(report['marker_cleanup'],'PASS')
            self.assertFalse(report['release_qualified'])
            self.assertEqual(report['instrumentation']['completed'],2)
            seq=['#'+m18.PREPARE, 'force-stop', '#'+m18.VERIFY]
            relevant=[str(a) for a in dev.commands if a[:2] in (('am','instrument'),('am','force-stop'))]
            self.assertIn(seq[0],relevant[0]);self.assertIn(seq[1],relevant[1]);self.assertIn(seq[2],relevant[2])
            self.assertNotIn('nonce',repr(report))
            self.assertFalse(report['m14_reexecuted'] or report['m15_reexecuted'] or report['m17_reexecuted'])

    def test_forbidden_device_mutations_absent(self):
        s=(HERE/'m18_device_qualification.py').read_text()
        self.assertNotIn("device.shell('pm','clear'",s)
        self.assertNotIn("device.shell('pm','uninstall'",s)
        self.assertNotIn("device.shell('reboot'",s)
        self.assertNotIn('device.instrument()',s)
        self.assertIn('m14.verify_artifacts(',s)
        self.assertIn('m14.verified_ci_checkout(',s)

if __name__=='__main__':unittest.main()
