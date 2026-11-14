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



class ApksignerFormatCompatibilityTests(unittest.TestCase):
    # These are synthetic examples of both Android build-tools output families.
    # No private keys or actual APK contents are used by these parser tests.
    def setUp(self):
        self.header = ("Verifies\n"
                       "Verified using v2 scheme (APK Signature Scheme v2): true\n"
                       "Number of signers: 1\n")
        self.v2 = "V2 Signer: certificate SHA-256 digest: " + EXPECTED_CERT + "\n"
        self.v3 = "V3.0 Signer: certificate SHA-256 digest: " + EXPECTED_CERT + "\n"
        self.v1 = "Signer #1 certificate SHA-256 digest: " + EXPECTED_CERT + "\n"

    def test_new_v2_only(self):
        self.assertEqual(apk_fingerprint(self.header + self.v2), EXPECTED_CERT)

    def test_new_v2_plus_v3_same_certificate(self):
        self.assertEqual(apk_fingerprint(self.header + self.v2 + self.v3), EXPECTED_CERT)

    def test_new_v2_plus_v3_and_v31_same_certificate(self):
        self.assertEqual(apk_fingerprint(self.header + self.v2 + self.v3 +
                         "V3.1 Signer: certificate SHA-256 digest: " + EXPECTED_CERT + "\n"), EXPECTED_CERT)

    def test_legacy_one_signer_and_count(self):
        self.assertEqual(apk_fingerprint(self.header + self.v1), EXPECTED_CERT)

    def test_wrong_v2_certificate(self):
        with self.assertRaisesRegex(Refused, "SIGNER_CERT_DOES_NOT_MATCH"):
            apk_fingerprint(self.header + self.v2.replace(EXPECTED_CERT, "f" * 64))

    def test_different_v3_certificate(self):
        with self.assertRaisesRegex(Refused, "SIGNER_CERT_DOES_NOT_MATCH"):
            apk_fingerprint(self.header + self.v2 + self.v3.replace(EXPECTED_CERT, "f" * 64))

    def test_two_v2_signers_even_when_same_certificate(self):
        with self.assertRaisesRegex(Refused, "APK_SIGNER_COUNT_NOT_ONE"):
            apk_fingerprint(self.header + self.v2 * 2)

    def test_non_one_declared_signer_count(self):
        with self.assertRaisesRegex(Refused, "APK_SIGNER_COUNT_NOT_ONE"):
            apk_fingerprint(self.header.replace("Number of signers: 1", "Number of signers: 2") + self.v2)

    def test_duplicated_count_lines(self):
        with self.assertRaisesRegex(Refused, "APK_SIGNER_COUNT_NOT_ONE"):
            apk_fingerprint(self.header + "Number of signers: 1\n" + self.v2)

    def test_missing_v2_scheme(self):
        with self.assertRaisesRegex(Refused, "APK_V2_SIGNATURE_NOT_VERIFIED"):
            apk_fingerprint("Number of signers: 1\n" + self.v2)

    def test_v2_false(self):
        with self.assertRaisesRegex(Refused, "APK_V2_SIGNATURE_NOT_VERIFIED"):
            apk_fingerprint(self.header.replace("v2): true", "v2): false") + self.v2)

    def test_scheme_v3_only_cannot_replace_v2(self):
        with self.assertRaisesRegex(Refused, "APK_SIGNER_COUNT_NOT_ONE"):
            apk_fingerprint(self.header + self.v3)

    def test_unknown_label_cannot_sneak_past_signer_count(self):
        with self.assertRaisesRegex(Refused, "APK_CERTIFICATE_SIGNER_LABEL_UNRECOGNIZED"):
            apk_fingerprint(self.header + self.v2 + "V2 Signer #2: certificate SHA-256 digest: " + EXPECTED_CERT + "\n")

    def test_min_sdk_rotation_label_is_not_assumed_safe(self):
        with self.assertRaisesRegex(Refused, "APK_CERTIFICATE_SIGNER_LABEL_UNRECOGNIZED"):
            apk_fingerprint(self.header + "Signer (minSdkVersion=24, maxSdkVersion=32) certificate SHA-256 digest: " + EXPECTED_CERT + "\n")

    def test_legacy_two_signers(self):
        with self.assertRaisesRegex(Refused, "APK_SIGNER_COUNT_NOT_ONE"):
            apk_fingerprint(self.header + self.v1 + self.v1.replace("#1", "#2"))

    def test_mixed_legacy_and_scheme_metadata(self):
        with self.assertRaisesRegex(Refused, "APK_SIGNER_FORMATS_MIXED"):
            apk_fingerprint(self.header + self.v1 + self.v2)

    def test_source_stamp_does_not_count_as_application_signer(self):
        self.assertEqual(apk_fingerprint(self.header + self.v2 +
          "Source Stamp Signer certificate SHA-256 digest: " + "f" * 64 + "\n"), EXPECTED_CERT)

    def test_only_source_stamp_refused(self):
        with self.assertRaisesRegex(Refused, "APK_SIGNER_COUNT_NOT_ONE"):
            apk_fingerprint(self.header + "Source Stamp Signer certificate SHA-256 digest: " + EXPECTED_CERT + "\n")

    def test_lookalike_public_key_digest_not_accepted(self):
        with self.assertRaisesRegex(Refused, "APK_SIGNER_COUNT_NOT_ONE"):
            apk_fingerprint(self.header + "V2 Signer: public key SHA-256 digest: " + EXPECTED_CERT + "\n")

    def test_bad_length_digest_refused(self):
        with self.assertRaisesRegex(Refused, "APK_CERTIFICATE_SIGNER_LABEL_UNRECOGNIZED"):
            apk_fingerprint(self.header + "V2 Signer: certificate SHA-256 digest: " + EXPECTED_CERT[:-1] + "\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
