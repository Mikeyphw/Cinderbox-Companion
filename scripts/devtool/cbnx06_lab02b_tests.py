#!/usr/bin/env python3
"""Fail-closed mutation tests for LAB02B transport and UI guards."""
import tempfile
import shutil
from pathlib import Path
import unittest
from cbnx06_lab02b_source_gate import ROOT, Refused, validate

PATHS={
 'transport':'app/src/main/java/com/sdvsync/steam/SteamClientManager.kt',
 'auth':'app/src/main/java/com/sdvsync/steam/SteamAuthenticator.kt',
 'settings':'app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt',
 'activity':'app/src/main/java/com/sdvsync/MainActivity.kt',
 'manifest':'app/src/cbnxLab/AndroidManifest.xml',
 'workflow':'.github/workflows/cbnx06-full-cinderbox-lab.yml',
}
class MutationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  validate(ROOT)
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='cbnx06-lab02b-neg-')
  self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
  for rel in PATHS.values():
   dst=self.root/rel;dst.parent.mkdir(parents=True,exist_ok=True)
   shutil.copy2(ROOT/rel,dst)
 def mutate(self,key,old,new,reason):
  file=self.root/PATHS[key];txt=file.read_text()
  self.assertEqual(txt.count(old),1, 'Source anchor unexpectedly duplicated/absent: '+old)
  file.write_text(txt.replace(old,new,1))
  with self.assertRaisesRegex(Refused,reason): validate(self.root)
 def test_steam_connect_guard(self):self.mutate('transport','check(!BuildConfig.CBNX_LAB) { "CBNX_LAB_STEAM_TRANSPORT_BLOCKED" }\n        if (_connectionState','if (_connectionState','LAB02B_STEAM_CONNECT_GUARD_MISSING')
 def test_steam_fallback_guard(self):self.mutate('transport','check(!BuildConfig.CBNX_LAB) { "CBNX_LAB_STEAM_TRANSPORT_BLOCKED" }\n        if (disconnectLatch','if (disconnectLatch','LAB02B_STEAM_CONNECTION_FALLBACK_UNGUARDED')
 def test_credential_login(self):self.mutate('auth','suspend fun login(username: String, password: String) {\n        check(!BuildConfig.CBNX_LAB) { "CBNX_LAB_STEAM_AUTH_FORBIDDEN" }','suspend fun login(username: String, password: String) {','LAB02B_STEAM_CREDENTIAL_ENTRY_UNGUARDED')
 def test_qr_login(self):self.mutate('auth','suspend fun loginWithQR() {\n        check(!BuildConfig.CBNX_LAB) { "CBNX_LAB_STEAM_AUTH_FORBIDDEN" }','suspend fun loginWithQR() {','LAB02B_STEAM_CREDENTIAL_ENTRY_UNGUARDED')
 def test_resume_login(self):self.mutate('auth','suspend fun loginWithSavedSession() {\n        check(!BuildConfig.CBNX_LAB) { "CBNX_LAB_STEAM_AUTH_FORBIDDEN" }','suspend fun loginWithSavedSession() {','LAB02B_STEAM_CREDENTIAL_ENTRY_UNGUARDED')
 def test_background_reconnect(self):self.mutate('auth','private fun requestSavedSessionRecovery(reason: String) {\n        if (BuildConfig.CBNX_LAB) return','private fun requestSavedSessionRecovery(reason: String) {','LAB02B_STEAM_AUTORECONNECT_UNGUARDED')
 def test_root_consent(self):self.mutate('settings','if (!BuildConfig.CBNX_LAB && confirmRoot)','if (confirmRoot)','LAB02B_PRIVILEGED_UI_UNGUARDED')
 def test_saf(self):self.mutate('settings','if (!BuildConfig.CBNX_LAB && state.safEligible)','if (state.safEligible)','LAB02B_PRIVILEGED_UI_UNGUARDED')
 def test_shizuku(self):self.mutate('settings','if (!BuildConfig.CBNX_LAB) {\n                Spacer(Modifier.height(12.dp))\n                ShizukuStatusSection(','if (true) {\n                Spacer(Modifier.height(12.dp))\n                ShizukuStatusSection(','LAB02B_PRIVILEGED_UI_UNGUARDED')
 def test_lab_banner(self):self.mutate('activity','cbnx06.lab.persistent-banner','generic.banner','LAB02B_PERSISTENT_LAB_IDENTITY_MISSING')
 def test_manifest(self):self.mutate('manifest','tools:replace="android:label"','tools:replace="android:allowBackup"','LAB02B_LAB_MANIFEST_REGRESSION')
 def test_workflow(self):self.mutate('workflow','python3 -B scripts/devtool/cbnx06_lab02b_source_gate.py','python3 -B scripts/devtool/cbnx06_source_gate.py','LAB02B_WORKFLOW_NOT_GATED')


class DeviceProbeTests(unittest.TestCase):
    """Synthetic ADB snapshots; no Android device is contacted."""
    def setUp(self):
        import json, hashlib
        self.temp=tempfile.TemporaryDirectory(prefix='cbnx-lab02b-adb-fixture-')
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.apk=root/'app-cbnxlab-debug.apk'
        self.apk.write_bytes(b'lab-fixture-'*14000)
        self.digest=hashlib.sha256(self.apk.read_bytes()).hexdigest()
        self.meta=root/'LAB_ARTIFACT_ATTESTATION.json'
        self.meta.write_text(json.dumps({
            'schema':'cbnx06-full-cinderbox-lab-v1',
            'source_sha':'a'*40,
            'application_id':'com.sdvsync.cbnx06lab',
            'apk_sha256':self.digest,
            'certificate_sha256':'b'*64,
            'lab_isolated_build':True,
            'physical_qualified':False
        }))
    def reply(self, serial, *args):
        if args[:2]==('shell','getprop'):
            return {'ro.build.version.sdk':'36', 'ro.product.cpu.abi':'arm64-v8a',
                    'ro.kernel.qemu':''}.get(args[-1],'')
        if args[:2]==('shell','pm'):
            return 'package:/data/app/'+args[-1]+'/base.apk'
        if args[:2]==('shell','sha256sum'):
            val=self.digest if 'cbnx06lab' in args[-1] else 'c'*64
            return val+'  '+args[-1]
        raise AssertionError('Unexpected ADB command '+str(args))
    def test_physical_read_only_identity_positive(self):
        from unittest.mock import patch
        from cbnx06_lab02b_device_probe import inspect
        with patch('cbnx06_lab02b_device_probe.adb',side_effect=self.reply):
            result=inspect('localhost:5555',self.apk,self.meta)
        self.assertTrue(result['physical_read_only_package_identity_qualified'])
        self.assertFalse(result['game_files_unchanged_qualified'])
        self.assertFalse(result['release_qualified'])
    def test_hosted_lab_apk_mismatch_is_refused(self):
        from unittest.mock import patch
        from cbnx06_lab02b_device_probe import inspect,Refused
        self.apk.write_bytes(b'tampered '+self.apk.read_bytes())
        with patch('cbnx06_lab02b_device_probe.adb',side_effect=self.reply):
            with self.assertRaisesRegex(Refused,'HOSTED_APK_ATTESTATION_MISMATCH'):
                inspect('localhost:5555',self.apk,self.meta)
    def test_installed_lab_absent_not_qualified(self):
        from unittest.mock import patch
        from cbnx06_lab02b_device_probe import inspect
        def no_lab(serial,*args):
            if args[:2]==('shell','pm') and args[-1]=='com.sdvsync.cbnx06lab':return ''
            return self.reply(serial,*args)
        with patch('cbnx06_lab02b_device_probe.adb',side_effect=no_lab):
            result=inspect('localhost:5555',self.apk,self.meta)
        self.assertFalse(result['physical_read_only_package_identity_qualified'])
    def test_malicious_pm_path_refused(self):
        from unittest.mock import patch
        from cbnx06_lab02b_device_probe import apk_path,Refused
        with patch('cbnx06_lab02b_device_probe.adb',return_value='package:/data/app/../sdcard/foo/base.apk'):
            with self.assertRaisesRegex(Refused,'INSTALLED_APK_PATH_INVALID'):
                apk_path('localhost:5555','com.sdvsync')
    def test_nonphysical_emulator_does_not_qualify(self):
        from unittest.mock import patch
        from cbnx06_lab02b_device_probe import inspect
        def emulator(serial,*args):
            if args==('shell','getprop','ro.kernel.qemu'):return '1'
            return self.reply(serial,*args)
        with patch('cbnx06_lab02b_device_probe.adb',side_effect=emulator):
            result=inspect('localhost:5555',self.apk,self.meta)
        self.assertFalse(result['physical_read_only_package_identity_qualified'])

if __name__=='__main__':unittest.main(verbosity=2)
