#!/usr/bin/env python3
"""Hermetic UX09D01 replacement: source, route safety, evidence and negative tests."""
from __future__ import annotations
import hashlib,json,pathlib,struct,sys,tempfile,unittest,zlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from ux09d01_gate import check,SCREENS
from ux09d01_report import analyze
from ux09d01_transform import patch_source,replace_once,patches,PREIMAGES

class SourceContracts(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='ux09d01-replacement-')
  self.root=pathlib.Path(self.tmp.name)
  source=pathlib.Path(__file__).resolve().parent
  for rel in ('app/src/main/java/com/sdvsync/ui/components/CinderboxBrandTopBar.kt',
    'app/src/androidTest/java/com/sdvsync/ui/ux/UxNormalChromeTest.kt',
    'scripts/devtool/ux09d01_report.py','scripts/devtool/ux09d01_emulator_ci.sh',
    '.github/workflows/cinderbox-ux09d01-normal-visual.yml'):
   dest=self.root/rel;dest.parent.mkdir(parents=True,exist_ok=True)
   real=ROOT/rel
   dest.write_bytes(real.read_bytes() if real.is_file() else (source/pathlib.Path(rel).name).read_bytes())
  for rel,steps in patches().items():
   sample='\n'.join(before for before,_ in steps)
   if rel.endswith('MainActivity.kt'):
    sample += '\nWindowInsets.statusBars\nstartDestination = "main"\nonConnectSteam\n' + 'onOpenOperationCenter = { parentNavController.navigate("operation_center") }\n'*2
   if rel.endswith('ApprovedModsScreen.kt'):
    sample += '\nonOpenQueue\nonBrowseMods\n'
   dest=self.root/rel;dest.parent.mkdir(parents=True,exist_ok=True)
   dest.write_text(patch_source(rel,sample))
  p=self.root/'docs/security/M3_RELEASE_POLICY.json';p.parent.mkdir(parents=True,exist_ok=True)
  p.write_text(json.dumps({k:False for k in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete')}))
  p=self.root/'app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt';p.parent.mkdir(parents=True,exist_ok=True)
  p.write_text('const val LIVE_UPDATES_ENABLED: Boolean = false\nconst val DEVICE_ACCEPTED: Boolean = false')
  ref=self.root/'design/cinderbox/01_REFERENCE/approved.html';ref.parent.mkdir(parents=True,exist_ok=True)
  ref.write_bytes(b'unchanged-approved-browser-reference')
  c=self.root/'design/cinderbox/02_CONTRACT/ux-contract.json';c.parent.mkdir(parents=True,exist_ok=True)
  c.write_text(json.dumps({'reference':{'sole_theme':'dark','path':'01_REFERENCE/approved.html','sha256':hashlib.sha256(ref.read_bytes()).hexdigest()},'screenshot_cases':{'count':24}}))
 def tearDown(self):self.tmp.cleanup()
 def modify(self,rel,old,new):
  p=self.root/rel;s=p.read_text();self.assertIn(old,s);p.write_text(s.replace(old,new,1))
 def test_contract(self):self.assertTrue(check(self.root))
 def test_exact_preimage_inventory(self):self.assertEqual(len(PREIMAGES),5)
 def test_double_patch_refused(self):
  for rel in PREIMAGES:
   with self.assertRaisesRegex(AssertionError,'PREIMAGE_MISMATCH'):
    patch_source(rel,(self.root/rel).read_text())
 def test_missing_anchor_refused(self):
  with self.assertRaisesRegex(AssertionError,'PREIMAGE_MISMATCH'):replace_once('wrong','old','new','guard')
 def test_old_glyph_actions_refused(self):
  p=self.root/'app/src/main/java/com/sdvsync/ui/components/CinderboxBrandTopBar.kt';p.write_text(p.read_text().replace('Text("Activity"','Text("↓"'))
  with self.assertRaises(AssertionError):check(self.root)
 def test_dead_global_action_refused(self):
  self.modify(SCREENS['saves'][0],'onOpenOperationCenter = onOpenOperationCenter','onOpenOperationCenter = {}')
  with self.assertRaisesRegex(AssertionError,'GLOBAL_ROUTE'):check(self.root)
 def test_missing_operation_center_route_refused(self):
  rel='app/src/main/java/com/sdvsync/ui/screens/OperationCenterScreen.kt'
  self.modify(rel,'testTag("cinderbox.screen.operation-center")','testTag("no.route")')
  with self.assertRaisesRegex(AssertionError,'OPERATION_CENTER_ROUTE_TAG_MISSING'):check(self.root)
 def test_missing_operation_back_refused(self):
  rel='app/src/main/java/com/sdvsync/ui/screens/OperationCenterScreen.kt'
  self.modify(rel,'testTag("cinderbox.operation-center.back")','testTag("no.back")')
  with self.assertRaisesRegex(AssertionError,'OPERATION_CENTER_ROUTE_TAG_MISSING'):check(self.root)
 def test_hosted_navigation_reliability_refused_if_removed(self):
  rel='app/src/androidTest/java/com/sdvsync/ui/ux/UxNormalChromeTest.kt'
  self.modify(rel,'UX09D01_STAGE_FAILED:', 'SILENT_FAILURE:')
  with self.assertRaisesRegex(AssertionError,'HOSTED_FUNCTIONAL_TEST_MISSING'):check(self.root)
 def test_missing_workflow_trigger_refused(self):
  rel='.github/workflows/cinderbox-ux09d01-normal-visual.yml'
  self.modify(rel,"      - 'app/src/main/java/com/sdvsync/MainActivity.kt'", "      - 'not/main.kt'")
  with self.assertRaisesRegex(AssertionError,'MISSING_MAIN_TRIGGER'):check(self.root)
 def test_missing_status_bar_contrast_refused(self):
  p='app/src/main/java/com/sdvsync/MainActivity.kt'
  self.modify(p,'SystemBarStyle.dark','SystemBarStyle.auto')
  with self.assertRaisesRegex(AssertionError,'LIGHT_STATUS_FOREGROUND'):check(self.root)
 def test_manager_buried_refused(self):
  self.modify(SCREENS['mods'][0],'Text("Manage local mods")','Text("No manager")')
  with self.assertRaisesRegex(AssertionError,'MANAGER_NOT_DISCOVERABLE'):check(self.root)
 def test_duplicate_manager_refused(self):
  p=self.root/SCREENS['mods'][0];p.write_text(p.read_text()+'\ntestTag("cinderbox.mods.advanced")\n')
  with self.assertRaisesRegex(AssertionError,'DUPLICATE_MANAGER_ACTION'):check(self.root)
 def test_functional_checks_cannot_disappear(self):
  p='app/src/androidTest/java/com/sdvsync/ui/ux/UxNormalChromeTest.kt'
  self.modify(p,'"cinderbox.screen.operation-center"','"no.route"')
  with self.assertRaisesRegex(AssertionError,'HOSTED_FUNCTIONAL_TEST_MISSING'):check(self.root)
 def test_no_scaling_work(self):
  self.modify('scripts/devtool/ux09d01_emulator_ci.sh','font_scale 1.0','font_scale 2.0')
  with self.assertRaises(AssertionError):check(self.root)
 def test_no_release_policy_changes(self):
  p=self.root/'docs/security/M3_RELEASE_POLICY.json';d=json.loads(p.read_text());d['release_enabled']=True;p.write_text(json.dumps(d))
  with self.assertRaisesRegex(AssertionError,'RELEASE_POLICY_CHANGED'):check(self.root)
 def test_reference_immutable(self):
  p=self.root/'design/cinderbox/01_REFERENCE/approved.html';p.write_bytes(p.read_bytes()+b'change')
  with self.assertRaisesRegex(AssertionError,'REFERENCE_DRIFT'):check(self.root)

def valid_png(dims, flat=False):
 w,h=dims
 header=struct.pack('>IIBBBBB',w,h,8,2,0,0,0)
 def chunk(tag,payload):
  return struct.pack('>I',len(payload))+tag+payload+struct.pack('>I',zlib.crc32(tag+payload)&0xffffffff)
 if flat:
  row=b'\x00'+bytes((16,24,32))*w
 else:
  palette=[(i*14, (i*39)%256, (i*65)%256) for i in range(16)]
  row=b'\x00'+b''.join(bytes(palette[(x//17)%len(palette)]) for x in range(w))
 raw=row*h
 return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',header)+
         chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))

class HostedEvidenceContracts(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='ux09d01-evidence-');self.root=pathlib.Path(self.tmp.name)
  for width,dims in {393:(786,1704),360:(720,1600)}.items():
   for case in ('mods','saves','more'):
    name=f'ux09d01-{case}-{width}'
    png=valid_png(dims)
    (self.root/(name+'.png')).write_bytes(png)
    from ux09d01_report import png_color_sample
    colors=png_color_sample(png,dims)
    (self.root/(name+'.json')).write_text(json.dumps({'case':case,'viewport':dims,'font_percent':100,'content_unique_colors':colors,
     'source':'real-offline-MainActivity','brand_top_px':48.0,'status_icons_light':True,
     'steam_login_attempted':False,'privileged_write_performed':False,
     'native_golden_approved':False,'physical_device_accepted':False}))
 def tearDown(self):self.tmp.cleanup()
 def audit(self):return analyze(self.root,'f'*40,'123')
 def test_six_default_font_screens(self):self.assertEqual(len(self.audit()['screens']),6)
 def test_no_dark_icons(self):
  p=self.root/'ux09d01-mods-360.json';j=json.loads(p.read_text());j['status_icons_light']=False;p.write_text(json.dumps(j))
  with self.assertRaisesRegex(AssertionError,'DARK_STATUS_ICONS'):self.audit()
 def test_refuse_nondefault_font(self):
  p=self.root/'ux09d01-more-393.json';j=json.loads(p.read_text());j['font_percent']=200;p.write_text(json.dumps(j))
  with self.assertRaisesRegex(AssertionError,'NOT_DEFAULT_FONT'):self.audit()
 def test_refuse_unapproved_golden_claim(self):
  p=self.root/'ux09d01-mods-393.json';j=json.loads(p.read_text());j['native_golden_approved']=True;p.write_text(json.dumps(j))
  with self.assertRaisesRegex(AssertionError,'FALSE_CLAIM'):self.audit()
 def test_refuse_status_overlap(self):
  p=self.root/'ux09d01-saves-360.json';j=json.loads(p.read_text());j['brand_top_px']=0;p.write_text(json.dumps(j))
  with self.assertRaisesRegex(AssertionError,'STATUS_OVERLAP'):self.audit()
 def test_refuse_wrong_png_size(self):
  p=self.root/'ux09d01-mods-360.png';p.write_bytes(valid_png((786,1600)))
  with self.assertRaisesRegex(AssertionError,'WRONG_SIZE'):self.audit()

 def test_refuse_fake_png_header(self):
  p=self.root/'ux09d01-more-360.png'
  p.write_bytes(b'\x89PNG\r\n\x1a\n'+b'FAKE'*400)
  with self.assertRaisesRegex(AssertionError,'PNG_'):self.audit()
 def test_refuse_corrupt_png_crc(self):
  p=self.root/'ux09d01-mods-393.png'; raw=bytearray(p.read_bytes())
  at=raw.index(b'IDAT')+8
  raw[at]^=1;p.write_bytes(raw)
  with self.assertRaisesRegex(AssertionError,'PNG_CRC_INVALID'):self.audit()
 def test_refuse_flat_blank_image(self):
  p=self.root/'ux09d01-saves-360.png';p.write_bytes(valid_png((720,1600),flat=True))
  with self.assertRaisesRegex(AssertionError,'BLANK_CONTENT'):self.audit()
 def test_refuse_forged_pixel_receipt(self):
  p=self.root/'ux09d01-more-393.json';d=json.loads(p.read_text())
  d['content_unique_colors']+=1;p.write_text(json.dumps(d))
  with self.assertRaisesRegex(AssertionError,'PIXEL_RECEIPT_MISMATCH'):self.audit()

if __name__=='__main__': unittest.main()
