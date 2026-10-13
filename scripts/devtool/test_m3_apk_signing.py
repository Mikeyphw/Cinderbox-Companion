"""Offline APK signing-block parsing regressions; no SDK/signing keys needed."""
from __future__ import annotations

import hashlib
from pathlib import Path
import os
import struct
import tempfile
import unittest
import zipfile

from m3_apk_signing import (
    APK_MAGIC, APK_V2_ID, APK_V3_ID, SigningBlockError,
    certificate_sha256, verified_signing_certificate,
)


def lp(data: bytes) -> bytes:
    return struct.pack('<I', len(data)) + data


def signature_value(leaf: bytes, second: bytes | None = None) -> bytes:
    signed_data = lp(b'') + lp(lp(leaf)) + lp(b'')
    signer = lp(signed_data) + lp(b'') + lp(b'')
    if second is not None:
        other_signed = lp(b'') + lp(lp(second)) + lp(b'')
        signer += lp(other_signed)
    return lp(lp(signer))


def signed_apk(target: Path, pairs: list[tuple[int, bytes]]) -> None:
    with zipfile.ZipFile(target, 'w') as archive:
        archive.writestr('AndroidManifest.xml', b'test')
        archive.writestr('classes.dex', b'dex')
    data = target.read_bytes()
    eocd = data.rfind(b'PK\x05\x06')
    assert eocd > 0
    cd_offset = struct.unpack_from('<I', data, eocd + 16)[0]
    records = b''.join(struct.pack('<QI', 4 + len(value), ident) + value for ident, value in pairs)
    size = len(records) + 24
    block = struct.pack('<Q', size) + records + struct.pack('<Q', size) + APK_MAGIC
    final = bytearray(data[:cd_offset] + block + data[cd_offset:])
    struct.pack_into('<I', final, eocd + len(block) + 16, cd_offset + len(block))
    target.write_bytes(final)


class SigningIdentityTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.apk = Path(self.folder.name) / 'fixture.apk'
        self.leaf = b'\x30\x04cert'  # only hash needed: DER verification occurs via OpenSSL downstream

    def test_reads_leaf_from_v2_block(self):
        signed_apk(self.apk, [(APK_V2_ID, signature_value(self.leaf))])
        self.assertEqual(verified_signing_certificate(self.apk), self.leaf)
        self.assertEqual(certificate_sha256(self.apk), hashlib.sha256(self.leaf).hexdigest())

    def test_accepts_matching_v2_and_v3_certificates(self):
        signed_apk(self.apk, [(APK_V2_ID, signature_value(self.leaf)), (APK_V3_ID, signature_value(self.leaf))])
        self.assertEqual(verified_signing_certificate(self.apk), self.leaf)

    def test_rejects_conflicting_schemes(self):
        signed_apk(self.apk, [(APK_V2_ID, signature_value(self.leaf)), (APK_V3_ID, signature_value(b'\x30diff'))])
        with self.assertRaisesRegex(SigningBlockError, 'disagree'):
            verified_signing_certificate(self.apk)

    def test_rejects_two_signers(self):
        # Append another signer to the one already encoded in length-prefixed sequence.
        signed_data = lp(b'') + lp(lp(self.leaf)) + lp(b'')
        signer = lp(signed_data) + lp(b'') + lp(b'')
        signed_apk(self.apk, [(APK_V2_ID, lp(lp(signer) + lp(signer)))])
        with self.assertRaisesRegex(SigningBlockError, 'exactly one APK signer'):
            verified_signing_certificate(self.apk)

    def test_rejects_duplicate_signature_scheme_id(self):
        signed_apk(self.apk, [(APK_V2_ID, signature_value(self.leaf)), (APK_V2_ID, signature_value(self.leaf))])
        with self.assertRaisesRegex(SigningBlockError, 'Duplicate'):
            verified_signing_certificate(self.apk)

    def test_rejects_unsigned_zip(self):
        with zipfile.ZipFile(self.apk, 'w') as archive:
            archive.writestr('classes.dex', b'foo')
        with self.assertRaisesRegex(SigningBlockError, 'No APK'):
            verified_signing_certificate(self.apk)

    def test_rejects_corrupt_signer_lengths(self):
        signed_apk(self.apk, [(APK_V2_ID, b'\xff' * 8)])
        with self.assertRaises(SigningBlockError):
            verified_signing_certificate(self.apk)

    @unittest.skipUnless(os.getenv('CINDERBOX_M3_TEST_APK'), 'Optional real signed APK fixture not supplied')
    def test_real_signing_block(self):
        apk = Path(os.environ['CINDERBOX_M3_TEST_APK'])
        cert = verified_signing_certificate(apk)
        self.assertGreater(len(cert), 100)
        self.assertEqual(len(certificate_sha256(apk)), 64)


if __name__ == '__main__':
    unittest.main()
