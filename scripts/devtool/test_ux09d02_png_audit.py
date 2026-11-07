#!/usr/bin/env python3
"""Hosted Pillow-only negative tests for evidence validator, not real UI proof."""
import json,pathlib,sys,tempfile,unittest
from PIL import Image,ImageDraw
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import ux09d02_report as report

class ImageAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=pathlib.Path(self.temp.name)
        self.original_cases=report.CASES
        self.original_viewports=report.VIEWPORTS
        report.CASES=('home',)
        report.VIEWPORTS={393:(786,1704)}
        self.stem='ux09d02-home-393'
        self.png=self.path/(self.stem+'.png')
        self.json=self.path/(self.stem+'.json')
        self.metadata={'case':'home','source':'real-offline-MainActivity','viewport':[786,1704],
                       'font_percent':100,'status_icons_light_requested':True,
                       'steam_auth_attempted':False,'privileged_write_performed':False,
                       'physical_device_qualified':False,'native_goldens_approved':False}
        self.json.write_text(json.dumps(self.metadata))

    def tearDown(self):
        report.CASES=self.original_cases
        report.VIEWPORTS=self.original_viewports
        self.temp.cleanup()

    def make_image(self, populated=True, icons=True):
        im=Image.new('RGB',(786,1704),(11,24,18))
        if populated:
            d=ImageDraw.Draw(im)
            for i in range(12):
                d.rectangle((80+i*4,420+i*70,600,448+i*70),fill=(30+i*10,55+i*5,40+i*7))
        if icons:
            ImageDraw.Draw(im).rectangle((630,20,690,35),fill=(245,245,245))
        im.save(self.png)

    def test_populated_dark_frame_accepted_without_golden_claim(self):
        self.make_image()
        receipt=report.verify(self.path,'0'*40,'123')
        self.assertEqual(len(receipt['screens']),1)
        self.assertFalse(receipt['native_goldens_approved'])
        self.assertFalse(receipt['physical_device_qualified'])

    def test_blank_frame_refused(self):
        self.make_image(populated=False)
        with self.assertRaisesRegex(ValueError,'BLANK_SCREEN'):
            report.verify(self.path,'0'*40,'123')

    def test_dark_status_icons_refused(self):
        self.make_image(icons=False)
        with self.assertRaisesRegex(ValueError,'DARK_STATUS_ICONS'):
            report.verify(self.path,'0'*40,'123')

    def test_missing_source_receipt_refused(self):
        self.make_image()
        self.json.unlink()
        with self.assertRaisesRegex(ValueError,'MISSING_EVIDENCE'):
            report.verify(self.path,'0'*40,'123')

if __name__=='__main__':
    unittest.main()
