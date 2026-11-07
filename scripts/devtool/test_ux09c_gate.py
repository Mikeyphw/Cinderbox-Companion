#!/usr/bin/env python3
"""Offline positive/negative source tests and zero-dependency PNG evidence checks."""
from __future__ import annotations
import hashlib,json,shutil,struct,tempfile,unittest
from pathlib import Path
from ux09c_gate import ROOT,REQUIRED,check
from ux09c_report import analyze

class UX09CSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='ux09c-gate-')
        self.root=Path(self.tmp.name)
        for n in REQUIRED:
            p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True)
            if (ROOT/n).is_file():shutil.copyfile(ROOT/n,p)
            else:
                mocks={
                 REQUIRED[4]:json.dumps({k:False for k in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete')}),
                 REQUIRED[5]: '\n'.join(f'val {k} = Color(0xFF{v})' for k,v in {'Background':'101915','Paper':'1B2922','Ink':'ECF5E9','Muted':'ACBDB0','Faint':'829B8A','Forest':'8CD9A8','Mint':'274936'}.items()),
                 REQUIRED[6]:'val liveBulkWritesAllowed: Boolean = false',
                 REQUIRED[7]:'const val LIVE_UPDATES_ENABLED: Boolean = false\nconst val DEVICE_ACCEPTED: Boolean = false',
                 REQUIRED[8]:json.dumps({'reference':{'sole_theme':'dark','path':'01_REFERENCE/cinderbox-portrait-DARK.html','sha256':hashlib.sha256(b'approved-dark').hexdigest()},'screenshot_cases':{'count':24}}),
                }
                p.write_text(mocks.get(n,''))
        contract=json.loads((self.root/REQUIRED[8]).read_text())
        html=self.root/'design/cinderbox'/contract['reference']['path']
        html.parent.mkdir(parents=True,exist_ok=True)
        if (ROOT/'design/cinderbox'/contract['reference']['path']).is_file():
            shutil.copyfile(ROOT/'design/cinderbox'/contract['reference']['path'],html)
        else:html.write_bytes(b'approved-dark')
    def tearDown(self):self.tmp.cleanup()
    def replace(self,n,old,new):
        p=self.root/n;s=p.read_text();self.assertIn(old,s);p.write_text(s.replace(old,new,1))
    def test_positive_contract(self):
        self.assertEqual(check(self.root)['result'],'UX09C01_A11Y_SOURCE_PASS')
    def test_rejects_lost_font_scale(self):
        self.replace(REQUIRED[1],'font_scale 2.0','font_scale 1.0')
        with self.assertRaisesRegex(AssertionError,'HOST_DRIVER_MISSING'):check(self.root)
    def test_rejects_credentialless_mods_search_input(self):
        self.replace(REQUIRED[0], 'assertIsNotEnabled()', 'performClick()')
        with self.assertRaisesRegex(AssertionError,'A11Y_ASSERTION'):check(self.root)
    def test_rejects_unsaved_real_ime_path_removal(self):
        self.replace(REQUIRED[0], 'ux09c_unsaved_ime_fixture', 'skipped')
        with self.assertRaisesRegex(AssertionError,'A11Y_ASSERTION'):check(self.root)
    def test_rejects_missing_diagnostic_receipt(self):
        self.replace(REQUIRED[1], 'UX09C_TEST_FAILURE_RECEIPT_', 'missing-evidence-')
        with self.assertRaisesRegex(AssertionError,'HOST_DRIVER_MISSING'):check(self.root)
    def test_rejects_tiny_touch_targets(self):
        self.replace(REQUIRED[0],'b.width >= 96f && b.height >= 96f','b.width >= 24f && b.height >= 24f')
        with self.assertRaisesRegex(AssertionError,'A11Y_ASSERTION'):check(self.root)
    def test_rejects_unsafe_file_access(self):
        self.replace(REQUIRED[0],'Espresso.pressBack()', 'restoreBackup()')
        with self.assertRaisesRegex(AssertionError,'A11Y_ASSERTION|FORBIDDEN_SIDE_EFFECT'):check(self.root)
    def test_rejects_low_contrast(self):
        self.replace(REQUIRED[5],'Color(0xFFECF5E9)','Color(0xFF202020)')
        with self.assertRaisesRegex(AssertionError,'LOW_COLOR_CONTRAST'):check(self.root)
    def test_rejects_release_policy_change(self):
        p=self.root/REQUIRED[4];j=json.loads(p.read_text());j['release_enabled']=True;p.write_text(json.dumps(j))
        with self.assertRaisesRegex(AssertionError,'POLICY_DRIFT'):check(self.root)
    def test_rejects_reference_drift(self):
        j=json.loads((self.root/REQUIRED[8]).read_text())
        p=self.root/'design/cinderbox'/j['reference']['path'];p.write_bytes(p.read_bytes()+b'x')
        with self.assertRaisesRegex(AssertionError,'REFERENCE_DRIFT'):check(self.root)

class UX09CEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='ux09c-evidence-');self.e=Path(self.tmp.name)
        for width,(w,h) in {393:(786,1704),360:(720,1600)}.items():
            for tab,tag in {'home':'cinderbox.screen.home','game':'cinderbox.screen.game',
                        'saves':'cinderbox.screen.saves','mods':'cinderbox.screen.mods',
                        'more':'cinderbox.screen.more'}.items():
                stem=f'{tab}-{width}';header=b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',w,h)
                (self.e/(stem+'.png')).write_bytes(header)
                (self.e/(stem+'.json')).write_text(json.dumps({'tab':tab,'screen_tag':tag,'width_dp':width,
                  'pixel_size':[w,h],'density':2.0,'font_scale':2.0,'real_offline_main_activity':True,
                  'provider_fixture':False,'local_storage_mutated':False,'interior_unique_colors':12,
                  'nav_targets':[{'tab':k,'width_px':120,'height_px':112}
                                  for k in ('HOME','DOWNLOAD','SAVES','MODS','SETTINGS')]}))
    def tearDown(self):self.tmp.cleanup()
    def run_report(self):return analyze(self.e,'a'*40,'123','b'*64,'c'*64)
    def test_report_ten(self):self.assertEqual(self.run_report()['actual_offline_screenshots'],10)
    def test_rejects_fake_steam_access(self):
        p=self.e/'game-393.json';x=json.loads(p.read_text());x['provider_fixture']=True;p.write_text(json.dumps(x))
        with self.assertRaises(AssertionError):self.run_report()
    def test_rejects_wrong_dimensions(self):
        p=self.e/'mods-360.png';b=bytearray(p.read_bytes());b[16:20]=struct.pack('>I',786);p.write_bytes(b)
        with self.assertRaisesRegex(AssertionError,'WRONG_PNG_SIZE'):self.run_report()
    def test_rejects_sub48dp_target(self):
        p=self.e/'more-393.json';x=json.loads(p.read_text());x['nav_targets'][0]['height_px']=70;p.write_text(json.dumps(x))
        with self.assertRaisesRegex(AssertionError,'TARGET_TOO_SMALL'):self.run_report()

if __name__=='__main__':unittest.main()
