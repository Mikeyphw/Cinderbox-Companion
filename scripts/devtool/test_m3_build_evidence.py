"""M3 fail-closed artifact-evidence tests. No SDK and no network needed."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("m3_evidence", HERE / "m3_build_evidence.py")
m3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m3)


class EvidenceContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.apks = self.root / "apks"
        self.apks.mkdir()
        self.apk = self.apks / "debug.apk"
        with zipfile.ZipFile(self.apk, "w") as z:
            z.writestr("AndroidManifest.xml", b"fake-manifest")
            z.writestr("classes.dex", b"fake-dex")
            z.writestr("assets/padding", b"x" * 5000)
        self.identity = dict(package_name="com.sdvsync", version_code=14, version_name="0.1.1",
                             signing_certificate_sha256="a"*64, signature_verified=True, debug_signed=True)
        self.sha = "b" * 40
        self.metadata = self.root / "M3_PROVENANCE.json"

    def tearDown(self):
        self.tmp.cleanup()

    def make_evidence(self):
        with patch.object(m3, "check_source"), patch.object(m3, "source_sha", return_value=self.sha), patch.object(m3, "inspect_android", return_value=self.identity):
            return m3.generate(self.root, self.apks, self.metadata, self.sha,
                               m3.EXPECTED_REPO, "refs/heads/security/m0-m1-hardening", "123")

    def test_roundtrip(self):
        doc = self.make_evidence()
        self.assertFalse(doc["qualified_release"])
        with patch.object(m3, "inspect_android", return_value=self.identity):
            self.assertEqual(m3.verify(self.apk, self.metadata, self.sha)["apk"]["sha256"], m3.sha256(self.apk))

    def test_mutation_detected(self):
        self.make_evidence()
        with self.apk.open("ab") as file:
            file.write(b"tamper")
        with patch.object(m3, "inspect_android", return_value=self.identity):
            with self.assertRaisesRegex(m3.QualificationError, "does not match"):
                m3.verify(self.apk, self.metadata, self.sha)

    def test_ref_must_match_trusted_run(self):
        self.make_evidence()
        with patch.object(m3, "inspect_android", return_value=self.identity):
            with self.assertRaisesRegex(m3.QualificationError, "source commit differs"):
                m3.verify(self.apk, self.metadata, "c" * 40)

    def test_release_claim_fails_closed(self):
        d = self.make_evidence()
        d["qualified_release"] = True
        self.metadata.write_text(json.dumps(d))
        with patch.object(m3, "inspect_android", return_value=self.identity):
            with self.assertRaisesRegex(m3.QualificationError, "qualification claim"):
                m3.verify(self.apk, self.metadata, self.sha)

    def test_bad_repository_rejected(self):
        with patch.object(m3, "check_source"), patch.object(m3, "source_sha", return_value=self.sha):
            with self.assertRaises(m3.QualificationError):
                m3.generate(self.root, self.apks, self.metadata, self.sha,
                            "attacker/repository", "refs/heads/master", "123")

    def test_multiple_apks_fail(self):
        (self.apks / "extra.apk").write_bytes(self.apk.read_bytes())
        with patch.object(m3, "check_source"), patch.object(m3, "source_sha", return_value=self.sha):
            with self.assertRaisesRegex(m3.QualificationError, "exactly one"):
                m3.generate(self.root, self.apks, self.metadata, self.sha,
                            m3.EXPECTED_REPO, "refs/heads/master", "123")

    def test_wrong_certificate_fails(self):
        with patch.object(m3, "certificate_sha256", return_value="a"*64), \
             patch.object(m3, "is_android_debug_certificate", return_value=False), \
             patch.object(m3, "_tool", side_effect=lambda s: s), patch.object(m3, "_run", side_effect=[
            "Signer #1 certificate SHA-256 digest: " + "a"*64 + "\nSigner #1 certificate DN: CN=Release Key\n",
            "package: name='com.sdvsync' versionCode='14' versionName='0.1.1'\n"]):
            with self.assertRaisesRegex(m3.QualificationError, "debug certificate"):
                m3.inspect_android(self.apk)

    def test_wrong_package_fails(self):
        with patch.object(m3, "certificate_sha256", return_value="a"*64), \
             patch.object(m3, "is_android_debug_certificate", return_value=True), \
             patch.object(m3, "_tool", side_effect=lambda s: s), patch.object(m3, "_run", side_effect=[
            "Signer #1 certificate SHA-256 digest: " + "a"*64 + "\nSigner #1 certificate DN: CN=Android Debug\n",
            "package: name='com.evil.app' versionCode='14' versionName='0.1.1'\n"]):
            with self.assertRaisesRegex(m3.QualificationError, "mismatched"):
                m3.inspect_android(self.apk)

    def test_source_policy_fails_open_release(self):
        policy_root = self.root
        file = policy_root / m3.POLICY_PATH
        file.parent.mkdir(parents=True)
        file.write_text(json.dumps(dict(release_enabled=True)))
        with self.assertRaises(m3.QualificationError):
            m3.validate_policy(policy_root)


if __name__ == "__main__":
    unittest.main()
