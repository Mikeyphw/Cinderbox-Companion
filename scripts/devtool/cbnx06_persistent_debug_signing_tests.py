#!/usr/bin/env python3
"""Offline, synthetic negative tests for CB-NX06 pinned-signature policy."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from cbnx06_persistent_debug_signing import (
    EXPECTED_CERT, Refused, attest, apk_fingerprint, keytool_fingerprint, preflight,
)


class SigningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dir = self.root / "artifacts"
        self.dir.mkdir()
        self.apk = self.dir / "app-debug.apk"
        self.apk.write_bytes(b"synthetic test APK only; never install")
        self.signer = self.root / "apksigner"
        self.signer.write_text("mock binary")
        self.sha = "a" * 40
        (self.dir / "SOURCE_ATTESTATION.json").write_text(json.dumps({
            "source_sha": self.sha,
            "apk_sha256": hashlib.sha256(self.apk.read_bytes()).hexdigest(),
            "release_qualified": False,
        }))
        self.cert = "Signer #1 certificate SHA-256 digest: " + EXPECTED_CERT
        self.output = "Verifies\nVerified using v2 scheme (APK Signature Scheme v2): true\n" + self.cert + "\n"

    def test_keystore_fingerprint_accepts_exact_pin(self):
        spaced = ":".join(EXPECTED_CERT[i:i + 2] for i in range(0, 64, 2))
        self.assertEqual(keytool_fingerprint("Certificate fingerprints:\n SHA256: " + spaced + "\n"), EXPECTED_CERT)

    def test_keystore_other_signer_refused(self):
        with self.assertRaisesRegex(Refused, "SIGNER_CERT_DOES_NOT_MATCH"):
            keytool_fingerprint(" SHA256: " + "a1:" * 31 + "a1\n")

    def test_keystore_ambiguous_fingerprint_refused(self):
        with self.assertRaisesRegex(Refused, "KEYSTORE_CERT_NOT_UNIQUE"):
            keytool_fingerprint("SHA256: " + EXPECTED_CERT + "\nSHA256: " + EXPECTED_CERT + "\n")

    def test_apk_matches_v2_and_one_signer(self):
        self.assertEqual(apk_fingerprint(self.output), EXPECTED_CERT)

    def test_apk_wrong_certificate_refused(self):
        with self.assertRaisesRegex(Refused, "SIGNER_CERT_DOES_NOT_MATCH"):
            apk_fingerprint(self.output.replace(EXPECTED_CERT, "f" * 64))

    def test_apk_second_signer_refused(self):
        with self.assertRaisesRegex(Refused, "APK_SIGNER_COUNT_NOT_ONE"):
            apk_fingerprint(self.output + "Signer #2 certificate SHA-256 digest: " + EXPECTED_CERT + "\n")

    def test_apk_absent_v2_refused(self):
        with self.assertRaisesRegex(Refused, "APK_V2_SIGNATURE_NOT_VERIFIED"):
            apk_fingerprint(self.cert + "\n")

    @patch("cbnx06_persistent_debug_signing.run_checked")
    def test_source_bound_attestation(self, run):
        run.return_value = self.output
        with patch.dict(os.environ, {"CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING": "true"}):
            doc = attest(self.apk, self.dir, self.sha, self.signer)
        self.assertEqual(doc["certificate_sha256"], EXPECTED_CERT)
        self.assertFalse(doc["installed_apk_bytes_verified_equal"])
        self.assertFalse(doc["release_qualified"])

    @patch("cbnx06_persistent_debug_signing.run_checked")
    def test_modified_apk_refused_before_signer(self, run):
        self.apk.write_bytes(b"modified")
        with patch.dict(os.environ, {"CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING": "true"}):
            with self.assertRaisesRegex(Refused, "SOURCE_ATTESTATION_NOT_MATCHING_APK"):
                attest(self.apk, self.dir, self.sha, self.signer)
        run.assert_not_called()

    @patch("cbnx06_persistent_debug_signing.run_checked")
    def test_no_signing_optin_refused(self, run):
        with patch.dict(os.environ, {"CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING": "false"}):
            with self.assertRaisesRegex(Refused, "PERSISTENT_SIGNING_NOT_MANDATORY"):
                attest(self.apk, self.dir, self.sha, self.signer)
        run.assert_not_called()

    @patch("cbnx06_persistent_debug_signing.run_checked")
    def test_preflight_missing_secrets_refused(self, run):
        keystore = self.root / "signer.p12"
        keystore.write_bytes(b"fake test only")
        keystore.chmod(0o600)
        with patch.dict(os.environ, {"CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING": "true",
                                   "CINDERBOX_DEBUG_STORE_PASSWORD": "", "CINDERBOX_DEBUG_KEY_PASSWORD": ""}):
            with self.assertRaisesRegex(Refused, "SIGNING_PASSWORD_SECRET_MISSING"):
                preflight(keystore)
        run.assert_not_called()

    @patch("cbnx06_persistent_debug_signing.run_checked")
    def test_preflight_wrong_signer_refused(self, run):
        keystore = self.root / "signer.p12"
        keystore.write_bytes(b"fake test only")
        keystore.chmod(0o600)
        run.return_value = " SHA256: " + "a1:" * 31 + "a1\n"
        with patch.dict(os.environ, {"CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING": "true",
                                   "CINDERBOX_DEBUG_STORE_PASSWORD": "synthetic",
                                   "CINDERBOX_DEBUG_KEY_PASSWORD": "synthetic"}):
            with self.assertRaisesRegex(Refused, "SIGNER_CERT_DOES_NOT_MATCH"):
                preflight(keystore)


if __name__ == "__main__":
    unittest.main(verbosity=2)
