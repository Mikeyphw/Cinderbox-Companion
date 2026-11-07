#!/usr/bin/env python3
"""HF01 source guard, pure stdlib and hermetic (safe before patches are applied)."""
import sys,unittest,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from ux09d01_hf01_patch import patch_source, replace_once,PREIMAGES

GATE='''for label in ('Your mods','Discover','Installed','Updates','Profiles',
                  'Browse mod catalog','No installed mods found',
                  'Check update metadata','No actionable updates listed',
                  'Manage profiles','Open advanced manager'):
        assert label in view,'UX05_APPROVED_COPY_MISSING:'+label
    for marker in ('ModManagerViewModel = koinViewModel()',
                   'state.installedMods'):
        assert marker in view
    assert 'Triple(BottomTab.MODS, "Your mods", "mods")' in r48
    assert 'rule.onNodeWithText("Your mods").assertExists()' in r48
'''
R48='''Triple(BottomTab.MODS, "Your mods", "mods"),
rule.onNodeWithText("Your mods").assertExists()
'''
VISUAL='''def independent_colors(img:Image.Image) -> int:
    w,h=img.size; colors=set()
    for y in range(h//4,(h*3)//4,23):
        for x in range(w//8,(w*7)//8,23):
            colors.add(img.getpixel((x,y)))
    return len(colors)
'''

class SourcePatchTests(unittest.TestCase):
 def test_three_pinned_preimages(self):
  self.assertEqual(len(PREIMAGES),3)
  self.assertTrue(all(len(s)==40 for s in PREIMAGES.values()))
 def test_ux05_title_and_manager_contract(self):
  p=patch_source('scripts/devtool/ux_05_mods_gate.py',GATE)
  self.assertIn("for label in ('Mods','Discover'",p)
  self.assertIn("'Manage profiles','Manage local mods'",p)
  self.assertIn('UX05_MODS_TITLE_MISSING',p)
  self.assertIn('UX05_MANAGER_ACTION_MISSING',p)
  self.assertNotIn('Open advanced manager',p)
 def test_ux05_invariants_not_removed(self):
  p=patch_source('scripts/devtool/ux_05_mods_gate.py',GATE)
  self.assertIn('state.installedMods',p)
  self.assertIn('UX05_APPROVED_COPY_MISSING',p)
  self.assertIn('for marker in',p)
 def test_r48_expectation_uses_unique_page_subtitle(self):
  p=patch_source('app/src/androidTest/java/com/sdvsync/qualification/R48RealActivityDeviceTest.kt',R48)
  self.assertEqual(p.count('"Discover, organize and customize."'),2)
  self.assertNotIn('"Your mods"',p)
 def test_visual_sampler_keeps_foreground_gate(self):
  p=patch_source('scripts/devtool/ux09b4_visual_audit.py',VISUAL)
  self.assertIn('foreground>=8',p)
  self.assertIn('UX09B4_NO_VISIBLE_FOREGROUND',p)
  self.assertIn('return len(colors)',p)
  self.assertIn('range(h//8,(h*7)//8,13)',p)
 def test_no_double_patch(self):
  for path,old in [('scripts/devtool/ux_05_mods_gate.py',GATE),
                   ('app/src/androidTest/java/com/sdvsync/qualification/R48RealActivityDeviceTest.kt',R48),
                   ('scripts/devtool/ux09b4_visual_audit.py',VISUAL)]:
   new=patch_source(path,old)
   with self.subTest(path=path),self.assertRaisesRegex(AssertionError,'PREIMAGE_MISMATCH'):
    patch_source(path,new)
 def test_missing_anchor_rejected(self):
  with self.assertRaisesRegex(AssertionError,'PREIMAGE_MISMATCH'):
   replace_once('wrong','expected','new','test')
 def test_duplicated_anchor_rejected(self):
  with self.assertRaisesRegex(AssertionError,'PREIMAGE_MISMATCH'):
   replace_once('aa','a','b','test')

if __name__=='__main__':unittest.main()
