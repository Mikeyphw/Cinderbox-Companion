#!/usr/bin/env python3
"""Negative receipt and PNG integrity checks; synthetic fixture only."""
import pathlib, struct, tempfile, unittest
import nex_r4_evidence as e
SHA='a'*40

def stub_png(width,height):
    # Shape-only stub for negative validation. Never an emulator screenshot.
    return (b'\x89PNG\r\n\x1a\n'+b'\x00\x00\x00\rIHDR'+struct.pack('>II',width,height)+
            b'\x08\x02\x00\x00\x00'+b'F'*3000+b'IEND\xaeB`\x82')

class EvidenceTest(unittest.TestCase):
    def fixture(self,root):
        for width,(w,h) in e.DIMENSIONS.items():
            for stage in e.STAGES:
                (root/f'{stage}-{width}.png').write_bytes(stub_png(w,h))
    def test_shape(self):
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t);self.fixture(p)
            self.assertEqual(len(e.inspect(p,SHA,'123')['images_sha256']),4)
    def test_wrong_source(self):
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t);self.fixture(p)
            with self.assertRaisesRegex(ValueError,'SOURCE_SHA'):e.inspect(p,'wrong','123')
    def test_missing_image(self):
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t);self.fixture(p);(p/'saved-card-360.png').unlink()
            with self.assertRaisesRegex(ValueError,'INVENTORY'):e.inspect(p,SHA,'123')
    def test_extra_diagnostic_refused_in_success(self):
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t);self.fixture(p);(p/'diagnostic-393.txt').write_text('failure')
            with self.assertRaisesRegex(ValueError,'INVENTORY'):e.inspect(p,SHA,'123')
    def test_wrong_dimensions(self):
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t);self.fixture(p)
            (p/'saved-card-393.png').write_bytes(stub_png(600,1704))
            with self.assertRaisesRegex(ValueError,'DIMENSIONS'):e.inspect(p,SHA,'123')
    def test_blank_or_truncated(self):
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t);self.fixture(p);(p/'offline-sheet-360.png').write_bytes(b'\x89PNG')
            with self.assertRaisesRegex(ValueError,'PNG_INVALID'):e.inspect(p,SHA,'123')

if __name__=='__main__': unittest.main(verbosity=2)
