#!/usr/bin/env python3
"""CB-NX06 HF01: real Gradle metadata contract and fail-closed negative fixtures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from cbnx06_debug_artifact import Refused, pack

SHA = "a" * 40

class TestArtifact(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cbnx06-hf01-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.debug = self.root / "app/build/outputs/apk/debug"
        self.debug.mkdir(parents=True)
        self.output = self.root / "out"
        self.apk = self.debug / "CinderboxCompanion-v0.1.1.apk"
        self.apk.write_bytes(b"fake debug APK bytes used only in unit tests\n")
        self.meta = {
            "version": 3,
            "artifactType": {"type": "APK", "kind": "Directory"},
            "applicationId": "com.sdvsync",
            "variantName": "debug",
            "elements": [{"type": "SINGLE", "filters": [], "attributes": [],
                          "versionCode": 14, "versionName": "0.1.1",
                          "outputFile": "CinderboxCompanion-v0.1.1.apk"}],
        }
        self.write_meta()

    def write_meta(self):
        (self.debug / "output-metadata.json").write_text(json.dumps(self.meta), encoding="utf-8")

    def refusal(self, code, mutator=None):
        if mutator:
            mutator()
        self.write_meta()
        with self.assertRaisesRegex(Refused, code):
            pack(self.debug, self.output, SHA)

    def test_correct_gradle_renamed_apk_emits_stable_bytes_and_sha(self):
        expected = hashlib.sha256(self.apk.read_bytes()).hexdigest()
        record = pack(self.debug, self.output, SHA)
        self.assertEqual((self.output / "app-debug.apk").read_bytes(), self.apk.read_bytes())
        self.assertEqual((self.output / "SHA256SUMS").read_text(), expected + "  app-debug.apk\n")
        self.assertEqual(json.loads((self.output / "SOURCE_ATTESTATION.json").read_text()), record)
        self.assertEqual(record["source_sha"], SHA)
        self.assertEqual(record["apk_sha256"], expected)
        self.assertFalse(any(record[k] for k in ("release_qualified", "live_nexus_qualified",
                                                 "live_firefox_qualified", "physical_arm64_qualified")))

    def test_missing_metadata(self):
        (self.debug / "output-metadata.json").unlink()
        with self.assertRaisesRegex(Refused, "GRADLE_METADATA_NOT_REGULAR"):
            pack(self.debug, self.output, SHA)

    def test_corrupt_metadata(self):
        (self.debug / "output-metadata.json").write_text("{bad", encoding="utf8")
        with self.assertRaisesRegex(Refused, "GRADLE_METADATA_INVALID_JSON"):
            pack(self.debug, self.output, SHA)

    def test_wrong_app_id(self):
        self.refusal("WRONG_APPLICATION_OR_VARIANT", lambda: self.meta.update(applicationId="com.example"))

    def test_wrong_variant(self):
        self.refusal("WRONG_APPLICATION_OR_VARIANT", lambda: self.meta.update(variantName="release"))

    def test_wrong_artifact_type(self):
        self.refusal("WRONG_OUTPUT_ARTIFACT_TYPE", lambda: self.meta.update(artifactType={"type": "AAR"}))

    def test_split_apk_disallowed(self):
        self.refusal("SPLIT_OR_INVALID_DEBUG_APK", lambda: self.meta["elements"][0].update(type="SPLIT"))

    def test_filtered_apk_disallowed(self):
        self.refusal("SPLIT_OR_INVALID_DEBUG_APK", lambda: self.meta["elements"][0].update(filters=[{"filterType":"ABI","value":"arm64-v8a"}]))

    def test_second_metadata_output(self):
        self.refusal("NOT_SINGLE_GRADLE_DEBUG_OUTPUT", lambda: self.meta["elements"].append(dict(self.meta["elements"][0])))

    def test_no_metadata_output(self):
        self.refusal("NOT_SINGLE_GRADLE_DEBUG_OUTPUT", lambda: self.meta.update(elements=[]))

    def test_wrong_filename_disallowed(self):
        self.refusal("GRADLE_OUTPUT_FILENAME_MISMATCH", lambda: self.meta["elements"][0].update(outputFile="app-debug.apk"))

    def test_directory_traversal_filename_disallowed(self):
        self.refusal("GRADLE_OUTPUT_FILENAME_MISMATCH", lambda: self.meta["elements"][0].update(outputFile="../some.apk"))

    def test_second_unexpected_apk(self):
        self.refusal("MULTIPLE_OR_UNEXPECTED_APKS", lambda: (self.debug / "extra.apk").write_bytes(b"fake"))

    def test_missing_apk(self):
        self.refusal("MULTIPLE_OR_UNEXPECTED_APKS", lambda: self.apk.unlink())

    def test_empty_apk(self):
        self.refusal("GRADLE_APK_UNSAFE_SIZE", lambda: self.apk.write_bytes(b""))

    def test_apk_symlink_disallowed(self):
        def change():
            other=self.root / "outside.apk";other.write_bytes(b"test")
            self.apk.unlink();self.apk.symlink_to(other)
        self.refusal("GRADLE_APK_NOT_REGULAR", change)

    def test_wrong_source_commit(self):
        with self.assertRaisesRegex(Refused, "SOURCE_SHA_INVALID"):
            pack(self.debug, self.output, "not-a-git-sha")

    def test_preexisting_artifact_is_not_overwritten(self):
        self.output.mkdir()
        (self.output / "app-debug.apk").write_bytes(b"old")
        with self.assertRaisesRegex(Refused, "OUTPUT_ALREADY_EXISTS"):
            pack(self.debug, self.output, SHA)
        self.assertEqual((self.output / "app-debug.apk").read_bytes(), b"old")

    def test_bad_version_rejected(self):
        self.refusal("UNSAFE_VERSION_NAME", lambda: self.meta["elements"][0].update(versionName="not safe !"))

    def test_metadata_symlink_disallowed(self):
        metadata=self.debug / "output-metadata.json"
        other=self.root / "outside.json";other.write_bytes(metadata.read_bytes())
        metadata.unlink();metadata.symlink_to(other)
        with self.assertRaisesRegex(Refused, "GRADLE_METADATA_NOT_REGULAR"):
            pack(self.debug, self.output, SHA)

    def test_output_dir_symlink_disallowed(self):
        target=self.root / "other"
        target.mkdir()
        self.output.symlink_to(target)
        with self.assertRaisesRegex(Refused, "OUTPUT_DIRECTORY_UNSAFE"):
            pack(self.debug, self.output, SHA)

if __name__ == "__main__":
    unittest.main(verbosity=2)
