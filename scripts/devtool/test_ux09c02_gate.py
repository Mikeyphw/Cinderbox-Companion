#!/usr/bin/env python3
"""Self-contained fail-closed regression checks; no Gradle or Android needed."""
from __future__ import annotations
import hashlib,json,struct,tempfile,unittest
from pathlib import Path
from ux09c02_gate import ROOT,PROD,check
from ux09c02_report import analyze
from ux09c02_transform import replace_once,main_activity

class SourceTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='ux09c02-tests-');self.root=Path(self.temp.name)
  for key,path in PROD.items():
   target=self.root/path;target.parent.mkdir(parents=True,exist_ok=True)
   src=ROOT/path
   if src.is_file():target.write_bytes(src.read_bytes())
   elif key=='policy':target.write_text(json.dumps({k:False for k in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete')}))
   elif key=='live':target.write_text('const val LIVE_UPDATES_ENABLED: Boolean = false\nconst val DEVICE_ACCEPTED: Boolean = false')
   elif key=='contract':
    data=b'approved-dark';path='01_REFERENCE/approved.html'
    target.write_text(json.dumps({'reference':{'sole_theme':'dark','path':path,'sha256':hashlib.sha256(data).hexdigest()},'screenshot_cases':{'count':24}}))
   else:
    available={
     'chrome':'AdvancedCinderboxChrome.kt',
     'androidtest':'UxDeviceChromeTest.kt',
     'workflow':'cinderbox-ux09c02-device-chrome.yml',
     'runner':'ux09c02_emulator_ci.sh',
     'report':'ux09c02_report.py',
    }
    if key in available and (Path(__file__).parent/available[key]).is_file():
     target.write_bytes((Path(__file__).parent/available[key]).read_bytes())
    elif key=='main':
     target.write_text('modifier = Modifier.fillMaxSize()\n            .windowInsetsPadding(WindowInsets.statusBars)\n            .consumeWindowInsets(WindowInsets.statusBars)\nonBack = { navController.popBackStack() },\n                onBrowseClick = {}')
    elif key=='login':
     target.write_text('CinderboxSteamLoginHeader(onBack = onContinueOffline)\nCinderboxSteamLoginIntroduction()\nModifier.testTag("cinderbox.steam-login.screen")\nRoundedCornerShape(12.dp)\n'+'\n'.join(['viewModel.login()', 'viewModel.loginWithQR()', 'viewModel.submit2FA()', 'viewModel.cancelQRLogin()', 'viewModel.tryResumeSession()', 'onOpenSettings']))
    elif key=='mods':
     target.write_text('CinderboxAdvancedModsHeader(\nonBack = onBack\nonBackups = { viewModel.refreshSafetyState(); showSnapshots = true }\nonUpdates = { viewModel.checkForUpdates() }\nonBrowse = onBrowseClick\nCinderboxAdvancedModsEmpty(\nstate.profiles.isNotEmpty()\nverticalScroll(rememberScrollState())\n'+'\n'.join(['viewModel::confirmPendingReview','viewModel::discardPendingReview','viewModel.restoreRetainedSnapshot','viewModel.importFromUri','viewModel.previewPortableImport','viewModel.dismissBulkPreview']))
    else:target.write_text('')
  c=json.loads((self.root/PROD['contract']).read_text())
  ref=self.root/'design/cinderbox'/c['reference']['path'];ref.parent.mkdir(parents=True,exist_ok=True)
  src=ROOT/'design/cinderbox'/c['reference']['path']
  ref.write_bytes(src.read_bytes() if src.is_file() else b'approved-dark')
 def tearDown(self):self.temp.cleanup()
 def mutate(self,key,old,new):
  path=self.root/PROD[key];s=path.read_text();self.assertIn(old,s);path.write_text(s.replace(old,new,1))
 def test_source_contract(self):self.assertIn('SOURCE_PASS',check(self.root)['result'])
 def test_refuse_dropped_status_padding(self):
  self.mutate('main','.windowInsetsPadding(WindowInsets.statusBars)', '.padding(top = 0.dp)')
  with self.assertRaisesRegex(AssertionError,'STATUS_INSET'):check(self.root)
 def test_refuse_return_button_mislabeled(self):
  self.mutate('login','CinderboxSteamLoginHeader(onBack = onContinueOffline)',
              'CinderboxSteamLoginHeader(onBack = {})')
  with self.assertRaises(AssertionError):check(self.root)
 def test_refuse_removed_review(self):
  self.mutate('mods','viewModel::confirmPendingReview','viewModel.skipReview')
  with self.assertRaisesRegex(AssertionError,'MOD_REVIEW'):check(self.root)
 def test_refuse_unauthorized_live_updates(self):
  self.mutate('live','LIVE_UPDATES_ENABLED: Boolean = false','LIVE_UPDATES_ENABLED: Boolean = true')
  with self.assertRaises(AssertionError):check(self.root)
 def test_refuse_reference_drift(self):
  c=json.loads((self.root/PROD['contract']).read_text());p=self.root/'design/cinderbox'/c['reference']['path']
  p.write_bytes(p.read_bytes()+b'junk')
  with self.assertRaisesRegex(AssertionError,'REFERENCE_CHANGED'):check(self.root)
 def test_patch_requires_unique_anchor(self):
  with self.assertRaisesRegex(AssertionError,'PREIMAGE_MISMATCH'):replace_once('aaa','a','x','bad')
 def test_main_patch_anchor(self):
  s='import androidx.compose.foundation.layout.navigationBars\n\n    NavHost(\n        navController = navController,\n        startDestination = "main",\n...\n            ModManagerScreen(\n                onBrowseClick = { navController.navigate("mods_browse") },'
  x=main_activity(s)
  self.assertIn('WindowInsets.statusBars',x)
  self.assertIn('onBack = { navController.popBackStack() }',x)

class EvidenceTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='ux09c02-proof-');self.root=Path(self.temp.name)
  for w,(pw,ph) in {393:(786,1704),360:(720,1600)}.items():
   for scale in (100,200):
    for case in ('home','steam','mods'):
     stem=f'ux09c02-{case}-{w}-{scale}'
     png=(b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',pw,ph))
     (self.root/(stem+'.png')).write_bytes(png)
     (self.root/(stem+'.json')).write_text(json.dumps({'case':case,'pixel_size':[pw,ph],
      'font_percent':scale,'content_top_px':48.0,'real_offline_main_activity':True,
      'steam_auth_performed':False,'mod_install_performed':False,
      'physical_device_qualified':False,'interior_unique_colors':12}))
 def tearDown(self):self.temp.cleanup()
 def run_report(self):return analyze(self.root,'a'*40,'123')
 def test_12_valid(self):self.assertEqual(self.run_report()['real_offline_screenshots'],12)
 def test_refuse_fake_steam_auth(self):
  p=self.root/'ux09c02-steam-393-100.json';d=json.loads(p.read_text());d['steam_auth_performed']=True;p.write_text(json.dumps(d))
  with self.assertRaises(AssertionError):self.run_report()
 def test_refuse_status_overlap(self):
  p=self.root/'ux09c02-home-360-200.json';d=json.loads(p.read_text());d['content_top_px']=0;p.write_text(json.dumps(d))
  with self.assertRaisesRegex(AssertionError,'STATUS_OVERLAP'):self.run_report()
 def test_refuse_wrong_png_size(self):
  p=self.root/'ux09c02-mods-360-100.png';b=bytearray(p.read_bytes());b[16:20]=struct.pack('>I',786);p.write_bytes(b)
  with self.assertRaisesRegex(AssertionError,'WRONG_SIZE'):self.run_report()

if __name__=='__main__':unittest.main()
