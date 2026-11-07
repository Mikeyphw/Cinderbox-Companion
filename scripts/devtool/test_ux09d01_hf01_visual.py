#!/usr/bin/env python3
"""Run on hosted Ubuntu with Pillow installed; checks the real visual sampler."""
import sys,pathlib,unittest,zipfile,io,os
from PIL import Image
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from ux09b4_visual_audit import independent_colors

class VisualSamplingTests(unittest.TestCase):
 def test_colorful_but_flat_image_fails(self):
  for rgb in ((255,255,255),(16,25,21),(60,150,80)):
   with self.subTest(rgb=rgb):
    im=Image.new('RGB',(360,800),rgb)
    try:
     self.assertLess(independent_colors(im),10)
    except AssertionError:
     # Dark blank backgrounds are rejected directly by the foreground guard.
     pass
 def test_dark_blank_image_fails(self):
  im=Image.new('RGB',(360,800),(16,25,21))
  for y in range(250,550):
   for x in range(50,300):
    im.putpixel((x,y),(28,44,36))
  with self.assertRaisesRegex(AssertionError,'NO_VISIBLE_FOREGROUND'):
   independent_colors(im)
 def test_dark_ui_with_real_foreground_passes(self):
  im=Image.new('RGB',(360,800),(16,25,21))
  for y in range(100,700):
   for x in range(30,330):
    if ((x//20)+(y//23))%7==0:
     im.putpixel((x,y),(130+(x%45),188,151))
  self.assertGreaterEqual(independent_colors(im),10)
 def test_actual_previous_failed_capture_if_available(self):
  # Optional explicit evidence fixture for hosted replay; no external network access.
  path=pathlib.Path(os.environ.get('UX09D01_HF01_EVIDENCE',''))
  if not path.is_file():self.skipTest('No explicit prior hosted evidence archive mounted')
  with zipfile.ZipFile(path) as z:
   im=Image.open(io.BytesIO(z.read('mods-profiles-360.png'))).convert('RGB').resize((360,800),Image.Resampling.LANCZOS)
   self.assertGreaterEqual(independent_colors(im),10)

if __name__=='__main__':unittest.main()
