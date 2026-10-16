"""M19 host gates: source, explicit consent, instrumentation, and process lifecycle."""
from argparse import Namespace
import json
from pathlib import Path
from unittest.mock import patch
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import m14_device_qualification as m14
import m19_device_qualification as m19

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

class M19HostTests(unittest.TestCase):
    def args(self,root,**changes):
        defaults=dict(repo=ROOT,run_id=123,ci_head='a'*40,transport='termux-root',
            force_stop_opt_in=True,ui_opt_in=True,test_profile_opt_in=True,
            install=True,allow_replace=True,output=Path(root)/'report.json')
        defaults.update(changes)
        return Namespace(**defaults)

    def test_exact_only_m19_methods_and_disposable_fixture(self):
        src=(ROOT/'app/src/androidTest/java/com/sdvsync/qualification/M19InterruptedRecoveryDeviceTest.kt').read_text()
        import re
        names=set(re.findall(r'@Test\s+fun\s+(\w+)\(',src))
        self.assertEqual(names,m19.TESTS)
        self.assertEqual(len(names),2)
        for term in ('createAndroidComposeRule<MainActivity>()',
                     'Continue offline','m19-test-only-',
                     'recovery.discard()', 'GameDownloadRecovery(f.journalRoot)'):
            self.assertIn(term,src)
        for forbidden in ('pm clear','pm uninstall','deleteRecursively','getExternalStorageDirectory',
                          'SteamAuthenticator.logout','System.exit','forceStopPackage','android.os.Process.killProcess'):
            self.assertNotIn(forbidden,src)

    def test_real_recovery_guard_and_sandbox_source_contract(self):
        src=(ROOT/'app/src/androidTest/java/com/sdvsync/qualification/M19InterruptedRecoveryDeviceTest.kt').read_text()
        for term in ('GameDownloadRecovery(f.journalRoot)', 'recovery.beginNew(',
                     'recovery.requireMatching(', 'checkpoint!!.matches(',
                     'assertArrayEquals(', 'duplicateRejected', 'mismatchRejected',
                     'OperationCenterPolicy.build(', 'CenterStatus.ACTION_REQUIRED',
                     'recovery.discard()', 'm19-test-only-'):
            self.assertIn(term,src)
        # Do not erase forensic fixtures on failed recovery assertions.
        self.assertNotIn('} finally {',src)
        self.assertIn('diagnostic evidence. Cleanup occurs only after all checks succeed.',src)
        self.assertNotIn('filesDir, "m6-game-download.properties"',src)
        for bad in ('SteamClientManager', 'GameDownloadManager(', 'ModDownloadManager(',
                    'Files.walk(', 'deleteRecursively(', 'getExternalStorageDirectory'):
            self.assertNotIn(bad,src)
        recovery=(ROOT/'app/src/main/java/com/sdvsync/download/GameDownloadRecovery.kt').read_text()
        self.assertIn('"m6-game-download.properties"',recovery)
        self.assertIn('"Resolve the previous download before starting another"',recovery)
        self.assertIn('"No matching interrupted download.',recovery)
        policy=(ROOT/'app/src/main/java/com/sdvsync/diagnostics/OperationCenterPolicy.kt').read_text()
        self.assertIn('"download" to "Interrupted game download"',policy)
        self.assertIn('"Check the original destination and options before resuming.',policy)

    def test_m19_fixture_canonicalizes_only_app_private_base(self):
        src=(ROOT/'app/src/androidTest/java/com/sdvsync/qualification/M19InterruptedRecoveryDeviceTest.kt').read_text()
        self.assertIn('targetContext.filesDir.canonicalFile',src)
        self.assertIn('File(privateFiles, "m19-test-only-$hash")',src)
        self.assertIn('M19_PRIVATE_FILES_UNSAFE',src)
        self.assertIn('!java.nio.file.Files.isSymbolicLink(privateFiles.toPath())',src)
        self.assertIn('!java.nio.file.Files.isSymbolicLink(root.toPath())',src)
        prod=(ROOT/'app/src/main/java/com/sdvsync/download/GameDownloadRecovery.kt').read_text()
        self.assertIn('Game directory contains a symbolic link',prod)
        self.assertIn('Files.isSymbolicLink(part.toPath())',prod)

    def test_sanitized_m19_failure_diagnostics_never_copy_paths_or_secrets(self):
        test=m19.PREPARE
        stack=('INSTRUMENTATION_STATUS: test='+test+'\n'
               'INSTRUMENTATION_STATUS: stack=java.lang.IllegalArgumentException: '
               'Game directory contains a symbolic link /data/user/0/com.sdvsync/files/SECRET\n'
               ' at com.sdvsync.download.GameDownloadRecovery$Companion.safeDestination('
               'GameDownloadRecovery.kt:44)\n'
               ' at com.sdvsync.qualification.M19InterruptedRecoveryDeviceTest.seedInterruptedDownloadCheckpoint('
               'M19InterruptedRecoveryDeviceTest.kt:58)\n'
               'INSTRUMENTATION_STATUS_CODE: -2\n')
        result=m19.sanitized_stage_failure(stack,test)
        self.assertEqual(result,{'category':'PRIVATE_PATH_ALIAS_REJECTED',
                                 'test_line':58,'recovery_line':44})
        self.assertNotIn('/data/',repr(result))
        self.assertNotIn('SECRET',repr(result))
        self.assertEqual(m19.sanitized_stage_failure('INSTRUMENTATION_CODE: -1',test)['category'],
                         'UNKNOWN')
        self.assertEqual(m19.sanitized_stage_failure(stack,'other'),
                         {'category':'UNKNOWN','test_line':None,'recovery_line':None})

    def test_ci_and_config_are_source_bound(self):
        for flow in ('build.yml','devtool-android-build.yml'):
            wf=(ROOT/'.github/workflows'/flow).read_text()
            self.assertIn(m19.CI_STEP,wf)
            self.assertIn("-p 'test_m19_*.py'",wf)
            self.assertEqual(wf.count('M14 compile isolated Android instrumentation APK'),1)
            self.assertIn('m16_debug_signing.py verify',wf)
        conf=(ROOT/'.devtool.toml').read_text()
        self.assertIn('[wrapper.commands.m19-check]',conf)
        self.assertIn('m19-check = ["job:m19-host"]',conf)
        source=(ROOT/'scripts/devtool/m14_device_qualification.py').read_text()
        self.assertGreaterEqual(source.count('feature/m19-interrupted-operation-recovery'),2)

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
                    self.assertEqual(m19.run(args),1)
                    cmd.assert_not_called()
                result=json.loads(args.output.read_text())
                self.assertEqual(result['failure_code'],expected)
                self.assertEqual(result['force_stop'],'NOT_RUN')
                self.assertEqual(result['install'],'NOT_RUN')
                self.assertFalse(result['release_qualified'])
                self.assertFalse(result['publication_allowed'])

    def test_instrumentation_failure_is_fail_closed(self):
        for s in ['INSTRUMENTATION_STATUS: test='+m19.PREPARE+'\nINSTRUMENTATION_STATUS_CODE: -2\nINSTRUMENTATION_CODE: -1\n',
                  'INSTRUMENTATION_STATUS: test='+m19.PREPARE+'\nINSTRUMENTATION_STATUS_CODE: 0\n',
                  'INSTRUMENTATION_CODE: -1\n']:
            with self.subTest(s=s):
                with self.assertRaises(m14.DeviceGateError):
                    m14.parse_instrumentation(s,{m19.PREPARE})

    def test_missing_process_or_invalid_launch_blocks(self):
        with self.assertRaises(m14.DeviceGateError):
            m19.assert_launch('Status: ok\nActivity: some.other.Activity')
        with self.assertRaises(m14.DeviceGateError):
            m19.assert_launch('Status: fail\nActivity: com.sdvsync/.MainActivity')
        m19.assert_launch('Status: ok\nActivity: com.sdvsync/.MainActivity\n')
        class Bad:
            def shell(self,*args,**kwargs): return 'unexpected response'
        with self.assertRaises(m14.DeviceGateError): m19.pid_of(Bad())
        class Stopped:
            def shell(self,*args,**kwargs): return ''
        self.assertFalse(m19.pid_of(Stopped()))

    def test_ci_requires_m19_gate(self):
        names=['M14 device qualification runner regressions',
               'M14 compile isolated Android instrumentation APK',
               'M14 upload isolated instrumentation APK',m19.CI_STEP]
        jobs=lambda seq:{'jobs':[{'steps':[{'name':x,'conclusion':'success'} for x in seq]}]}
        with patch('m13_qualification.assess_ci',return_value={}):
            m19.verify_ci({'head_branch':'feature/m19-interrupted-operation-recovery'},jobs(names),'a'*40)
            with self.assertRaises(m14.DeviceGateError):
                m19.verify_ci({'head_branch':'feature/m19-interrupted-operation-recovery'},jobs(names[:-1]),'a'*40)
            with self.assertRaises(m14.DeviceGateError):
                m19.verify_ci({'head_branch':'feature/m17-android-ui-lifecycle'},jobs(names),'a'*40)

    def test_full_mocked_flow_real_force_stop_between_two_stages(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            args=self.args(td)
            dev=FakeDevice()
            provenance={'source_commit':'b'*40,'source_ref':'refs/pull/23/merge'}
            metadata={'head_branch':'feature/m19-interrupted-operation-recovery'}
            def gh(args):
                if args[0].endswith('jobs?per_page=100'):
                    return {'jobs':[{'steps':[{'name':m19.CI_STEP,'conclusion':'success'}]}]}
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
                 patch.object(m19,'verify_ci'),\
                 patch.object(m14,'read_json',return_value=provenance),\
                 patch.object(m14,'verified_ci_checkout',return_value=('b'*40,'refs/pull/23/merge')),\
                 patch.object(m14,'verify_artifacts',return_value=(td/'a.apk',td/'t.apk','c'*64,'d'*64)),\
                 patch.object(m14,'Transport',return_value=dev):
                self.assertEqual(m19.run(args),0)
            report=json.loads(args.output.read_text())
            self.assertEqual(report['overall'],'PASS_INTERRUPTED_OPERATION_RECOVERY_AUTOMATION')
            self.assertEqual(report['force_stop'],'PASS')
            self.assertEqual(report['process_gone'],'PASS')
            self.assertEqual(report['fixture_cleanup'],'PASS')
            self.assertFalse(report['release_qualified'])
            self.assertEqual(report['instrumentation']['completed'],2)
            seq=['#'+m19.PREPARE, 'force-stop', '#'+m19.VERIFY]
            relevant=[str(a) for a in dev.commands if a[:2] in (('am','instrument'),('am','force-stop'))]
            self.assertIn(seq[0],relevant[0]);self.assertIn(seq[1],relevant[1]);self.assertIn(seq[2],relevant[2])
            self.assertNotIn('nonce',repr(report))
            self.assertFalse(report['m14_reexecuted'] or report['m15_reexecuted'] or report['m17_reexecuted'] or report['m18_reexecuted'])

    def test_forbidden_device_mutations_absent(self):
        s=(HERE/'m19_device_qualification.py').read_text()
        self.assertNotIn("device.shell('pm','clear'",s)
        self.assertNotIn("device.shell('pm','uninstall'",s)
        self.assertNotIn("device.shell('reboot'",s)
        self.assertNotIn('device.instrument()',s)
        self.assertIn('m14.verify_artifacts(',s)
        self.assertIn('m14.verified_ci_checkout(',s)

if __name__=='__main__':unittest.main()
