"""M17: source-bound offline UI and lifecycle qualification host invariants."""
import json
from pathlib import Path
from argparse import Namespace
from unittest.mock import patch
import re
import sys
import tempfile
import unittest

from ci_workflow_contract import effective_ci_source
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import m14_device_qualification as m14
import m17_device_qualification as m17

class M17HostTests(unittest.TestCase):
    def test_exact_ui_methods(self):
        src=(ROOT/'app/src/androidTest/java/com/sdvsync/qualification/M17OfflineUiDeviceTest.kt').read_text()
        methods=set(re.findall(r'@Test\s+fun\s+([A-Za-z][A-Za-z0-9_]*)\s*\(',src))
        self.assertEqual(methods,m17.TESTS)
        self.assertEqual(len(methods),4)
        self.assertIn('createAndroidComposeRule<MainActivity>()',src)
        self.assertIn('activityRule.scenario.recreate()',src)
        self.assertIn('Continue offline',src)
        self.assertIn('Live, read-only status and recovery guidance',src)
        for forbidden in ['clearApplicationUserData','pm uninstall','getExternalStorageDirectory','deleteRecursively','SteamAuthenticator.logout','grantRuntimePermission']:
            self.assertNotIn(forbidden,src)

    def test_compose_assert_exists_is_interaction_method_not_top_level_import(self):
        src=(ROOT/'app/src/androidTest/java/com/sdvsync/qualification/M17OfflineUiDeviceTest.kt').read_text()
        # Compile-time contract: assertExists belongs to SemanticsNodeInteraction;
        # importing androidx.compose.ui.test.assertExists breaks Kotlin compilation.
        self.assertNotIn('import androidx.compose.ui.test.assertExists', src)
        self.assertIn('.assertExists()', src)

    def test_settings_control_scrolls_before_touch_click(self):
        src=(ROOT/'app/src/androidTest/java/com/sdvsync/qualification/M17OfflineUiDeviceTest.kt').read_text()
        self.assertIn('rule.onNodeWithText("Settings").performScrollTo().performClick()',src)
        self.assertNotIn('rule.onNodeWithText("Settings").performClick()',src)

    def test_failure_diagnostics_are_allowlisted_and_path_free(self):
        sample = ("INSTRUMENTATION_STATUS: test=signedOutSettingsAreAccessibleWithoutSteamLogin\n"
                  "INSTRUMENTATION_STATUS: stack=java.lang.AssertionError: Failed to perform a click "
                  "account=PRIVATE token=SECRET at /data/user/0/abc/secret "
                  "\n at com.sdvsync.qualification.M17OfflineUiDeviceTest.settingsFromLogin(M17OfflineUiDeviceTest.kt:38)\n"
                  "INSTRUMENTATION_STATUS_CODE: -2\n")
        got=m17.sanitized_failure_sites(sample)
        self.assertEqual(got,{'signedOutSettingsAreAccessibleWithoutSteamLogin':
                              {'category':'NODE_OFFSCREEN','test_line':38}})
        self.assertNotIn('PRIVATE',repr(got))
        self.assertNotIn('SECRET',repr(got))
        self.assertNotIn('/data/',repr(got))
        self.assertEqual(m17.sanitized_failure_sites('INSTRUMENTATION_CODE: -1'),{})
        self.assertEqual(m17.sanitized_failure_sites(
            'INSTRUMENTATION_STATUS: test=otherTest\nINSTRUMENTATION_STATUS: stack=Error\n'
            'INSTRUMENTATION_STATUS_CODE: -2\n'),{})

    def test_espresso_370_is_explicitly_instrumentation_only(self):
        gradle=(ROOT/'app/build.gradle.kts').read_text()
        pin='androidTestImplementation("androidx.test.espresso:espresso-core:3.7.0")'
        self.assertIn(pin,gradle)
        self.assertEqual(gradle.count(pin),1)
        self.assertNotIn('debugImplementation("androidx.test.espresso:espresso-core',gradle)
        self.assertNotIn('implementation("androidx.test.espresso:espresso-core',gradle)
        self.assertIn('androidTestImplementation("androidx.compose.ui:ui-test-junit4")',gradle)

    def test_framework_reflection_failure_is_classified_without_raw_details(self):
        test='signedOutSettingsAreAccessibleWithoutSteamLogin'
        head=f'INSTRUMENTATION_STATUS: test={test}\nINSTRUMENTATION_STATUS: stack='
        tail='\nINSTRUMENTATION_STATUS_CODE: -2\n'
        raw=head + ('java.util.concurrent.ExecutionException: java.lang.RuntimeException: '
                     'java.lang.NoSuchMethodException: android.hardware.input.InputManager.getInstance() '
                     'account=PRIVATE_KEY /data/user/0/secret') + tail
        self.assertEqual(m17.sanitized_failure_sites(raw), {test: {
            'category': 'ESPRESSO_INPUT_MANAGER_REFLECTION','test_line': None}})
        generic=head+'java.lang.NoSuchMethodException: secret.Private.method()'+tail
        self.assertEqual(m17.sanitized_failure_sites(generic), {test: {
            'category':'FRAMEWORK_REFLECTIVE_METHOD_MISSING','test_line':None}})
        self.assertNotIn('PRIVATE_KEY',repr(m17.sanitized_failure_sites(raw)))
        self.assertNotIn('/data/',repr(m17.sanitized_failure_sites(raw)))

    def test_opt_in_fails_before_gh_or_install(self):
        with tempfile.TemporaryDirectory() as temp:
            result=Path(temp)/'result.json'
            args=Namespace(repo=Path(temp), run_id=1, ci_head=None, transport='termux-root',
                           install=True, allow_replace=True, ui_opt_in=False,output=result)
            with patch.object(m14,'command') as cmd:
                self.assertEqual(m17.run(args),1)
                cmd.assert_not_called()
            report=json.loads(result.read_text())
            self.assertEqual(report['failure_code'],'LIVE_UI_REQUIRES_EXPLICIT_FLAG')
            self.assertEqual(report['install'],'NOT_RUN')
            self.assertEqual(report['instrumentation'],'NOT_RUN')
            self.assertFalse(report['live_ui_opt_in'])
            for key in ('release_qualified','publication_allowed','device_qualified','automatic_device_install','automatic_uninstall','m14_reexecuted','m15_reexecuted'):
                self.assertIs(report[key],False)

    def test_install_opt_in_required_too(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'result.json'
            args=Namespace(repo=Path(temp),run_id=1,ci_head=None,transport='termux-root',
                           install=False,allow_replace=False,ui_opt_in=True,output=output)
            with patch.object(m14,'command') as cmd:
                self.assertEqual(m17.run(args),1)
                cmd.assert_not_called()
            self.assertEqual(json.loads(output.read_text())['failure_code'],'INSTALL_REQUIRES_EXPLICIT_FLAG')

    def test_m17_ci_requires_own_step_plus_existing_ci(self):
        names=['M14 device qualification runner regressions',
               'M14 compile isolated Android instrumentation APK',
               'M14 upload isolated instrumentation APK',m17.M17_CI_STEP]
        jobs=lambda seq:{'jobs':[{'steps':[{'name':name,'conclusion':'success'} for name in seq]}]}
        with patch('m13_qualification.assess_ci',return_value={}):
            m17.verify_m17_ci({'head_branch':'feature/m17-android-ui-lifecycle'},jobs(names),'a'*40)
            with self.assertRaises(m14.DeviceGateError):
                m17.verify_m17_ci({'head_branch':'feature/m17-android-ui-lifecycle'},jobs(names[:-1]),'a'*40)
            with self.assertRaises(m14.DeviceGateError):
                m17.verify_m17_ci({'head_branch':'feature/m16-persistent-debug-signing'},jobs(names),'a'*40)

    def test_strict_instrumentation_parser(self):
        sample=''.join(f'INSTRUMENTATION_STATUS: test={name}\nINSTRUMENTATION_STATUS_CODE: 0\n'
                       for name in sorted(m17.TESTS))+'INSTRUMENTATION_CODE: -1\n'
        self.assertEqual('PASS',m14.parse_instrumentation(sample,m17.TESTS)['status'])
        for modified in [sample.replace('INSTRUMENTATION_CODE: -1','INSTRUMENTATION_CODE: 0'),
                         sample.replace('INSTRUMENTATION_CODE: -1',''),
                         sample.replace('INSTRUMENTATION_STATUS_CODE: 0','INSTRUMENTATION_STATUS_CODE: -2',1),
                         sample.replace('INSTRUMENTATION_CODE: -1','INSTRUMENTATION_CODE: -1\nINSTRUMENTATION_CODE: -1')]:
            with self.assertRaises(m14.DeviceGateError):
                m14.parse_instrumentation(modified,m17.TESTS)

    def test_ci_and_gradle_dependencies_without_duplicate_build(self):
        workflow=(ROOT/'.github/workflows/build.yml').read_text()
        devtool=effective_ci_source(ROOT,'.github/workflows/devtool-android-build.yml')
        for body in [workflow,devtool]:
            self.assertIn(m17.M17_CI_STEP,body)
            self.assertIn("-p 'test_m17_*.py'",body)
            self.assertEqual(1,body.count('M14 compile isolated Android instrumentation APK'))
            self.assertIn('m16_debug_signing.py verify',body)
        gradle=(ROOT/'app/build.gradle.kts').read_text()
        self.assertIn('androidTestImplementation("androidx.compose.ui:ui-test-junit4")',gradle)
        self.assertIn('debugImplementation("androidx.compose.ui:ui-test-manifest")',gradle)
        self.assertIn('signingConfigs.getByName("ciDebug")',gradle)
        source=(HERE/'m17_device_qualification.py').read_text()
        self.assertIn('device.instrument(test_class=CLASS)',source)
        self.assertNotIn('device.instrument()',source)
        self.assertNotIn('pm uninstall',source)
        self.assertNotIn('pm clear',source)
        self.assertIn('m14.verify_artifacts(',source)
        self.assertIn('m14.verified_ci_checkout(',source)

if __name__=='__main__': unittest.main()
