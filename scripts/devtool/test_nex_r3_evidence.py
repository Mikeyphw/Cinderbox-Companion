"""PNG/source integrity negative tests; no Android or Nexus secrets required."""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
import nex_r3_evidence as evidence


def chunk(kind, data):
    return (struct.pack('>I', len(data)) + kind + data +
            struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff))


def synthetic_png(width, height):
    # A small, genuinely decodable grayscale PNG with random-looking row samples.
    import random
    rng = random.Random(width * 11 + height)
    pixels = bytearray()
    for _ in range(height):
        pixels.append(0)  # Filter type None.
        pixels.extend(rng.randbytes(width))
    hdr = struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', hdr) +
            chunk(b'IDAT', zlib.compress(bytes(pixels), 6)) + chunk(b'IEND', b''))


class EvidenceTests(unittest.TestCase):
    def populated(self, tmp):
        root = Path(tmp)
        for label in evidence.STAGES:
            for dp, (w, h) in evidence.DIMENSIONS.items():
                (root / f'{label}-{dp}.png').write_bytes(synthetic_png(w, h))
        return root

    def test_complete_synthetic_provenance_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = evidence.verify(self.populated(tmp), 'a' * 40, '42446450123')
            self.assertEqual(18, len(receipt['screenshots']))
            self.assertFalse(receipt['live_nexus_schema_qualified_by_this_run'])
            self.assertFalse(receipt['release_qualified'])
            self.assertTrue(receipt['provider_responses_are_synthetic'])

    def test_missing_screenshot_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.populated(tmp)
            (root / 'no-key-360.png').unlink()
            with self.assertRaisesRegex(ValueError, 'SCREENSHOT_INVENTORY'):
                evidence.verify(root, 'a' * 40, '123')

    def test_unexpected_extra_png_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.populated(tmp)
            (root / 'key-exposed.png').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError, 'SCREENSHOT_INVENTORY'):
                evidence.verify(root, 'a' * 40, '123')

    def test_false_source_sha_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'SOURCE_PIN'):
                evidence.verify(Path(tmp), 'not-a-commit', '123')

    def test_bad_viewport_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.populated(tmp)
            (root / 'detail-360.png').write_bytes(synthetic_png(500, 500))
            with self.assertRaisesRegex(ValueError, 'VIEWPORT'):
                evidence.verify(root, 'a' * 40, '123')

    def test_truncated_or_corrupt_png_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.populated(tmp)
            file = root / 'detail-360.png'
            file.write_bytes(file.read_bytes()[:120])
            with self.assertRaisesRegex(ValueError, 'PNG'):
                evidence.verify(root, 'a' * 40, '123')

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.populated(tmp)
            old = root / 'detail-360.png'
            target = root / 'returned-360.png'
            old.unlink()
            old.symlink_to(target.name)
            with self.assertRaisesRegex(ValueError, 'SYMLINK'):
                evidence.verify(root, 'a' * 40, '123')


if __name__ == '__main__':
    unittest.main(verbosity=2)
