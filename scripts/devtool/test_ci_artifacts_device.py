"""Fast offline, no-device tests for the selective CI artifact/install qualification CLI."""
from __future__ import annotations

import contextlib
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ci_artifacts_device as ci


class Tests(unittest.TestCase):
    def test_dynamic_lanes_and_explicit_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts" / "devtool"
            scripts.mkdir(parents=True)
            (scripts / "m24_pics_device_run.py").write_text("# synthetic\n")
            (scripts / "future_owned_device_run.py").write_text("# synthetic\n")
            (scripts / "not_a_runner.py").write_text("# not a lane\n")
            mapping = ci.lanes(root)
            self.assertEqual(set(mapping), {"m24-pics", "future-owned"})
            self.assertEqual([x[0] for x in ci.select_lanes(mapping, ["m24-pics,future-owned", "m24-pics"])],
                             ["m24-pics", "future-owned"])
            with self.assertRaisesRegex(ci.QualificationError, "UNKNOWN_TEST_LANE"):
                ci.select_lanes(mapping, ["m99"])

    def test_ci_must_be_exact_and_successful(self):
        sha = "a" * 40
        payload = {"id": 12, "status": "completed", "conclusion": "success", "head_sha": sha,
                   "repository": {"full_name": ci.DEFAULT_REPO}}
        import json
        with patch.object(ci, "command", return_value=json.dumps(payload)):
            self.assertEqual(ci.verified_run(12, ci.DEFAULT_REPO, expected_sha=sha)["id"], 12)
            with self.assertRaisesRegex(ci.QualificationError, "CI_COMMIT_MISMATCH"):
                ci.verified_run(12, ci.DEFAULT_REPO, expected_sha="b" * 40)
        for bad in ({**payload, "conclusion": "failure"},
                    {**payload, "repository": {"full_name": "unknown/repo"}},
                    {**payload, "head_sha": "bad"}):
            with patch.object(ci, "command", return_value=json.dumps(bad)):
                with self.assertRaises(ci.QualificationError):
                    ci.verified_run(12, ci.DEFAULT_REPO, expected_sha=None)

    def test_artifact_and_test_receipt_fail_closed(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "app.apk").write_bytes(b"apk")
            self.assertEqual(ci.one_apk(folder).name, "app.apk")
            (folder / "another.apk").write_bytes(b"apk")
            with self.assertRaisesRegex(ci.QualificationError, "ARTIFACT_APK_COUNT"):
                ci.one_apk(folder)
            (folder / "another.apk").unlink()
            receipt = folder / "test.json"
            pass_doc = {"overall": "PASS_FOUR_PRIVATE", "completed": 2,
                        "expected_cases": 2, "cases": {"one": "PASS", "two": "PASS"}}
            receipt.write_text(json.dumps(pass_doc))
            self.assertEqual(ci.verify_receipt(receipt, "lane")["completed"], 2)
            receipt.write_text(json.dumps({**pass_doc, "cases": {"one": "PASS", "two": "FAIL"}}))
            with self.assertRaisesRegex(ci.QualificationError, "TEST_LANE_NOT_PASS"):
                ci.verify_receipt(receipt, "lane")

    def test_successful_pair_proof_and_selected_lane_without_real_device(self):
        import json
        sha = "b" * 40
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "checkout" / "scripts" / "devtool"
            source.mkdir(parents=True)
            (source / "fixture_device_run.py").write_text("# synthetic\n")
            commands = []
            def fake(args, **kwargs):
                commands.append(args)
                if args[:2] == ["gh", "api"]:
                    return json.dumps({"id": 123, "repository": {"full_name": ci.DEFAULT_REPO},
                                      "status": "completed", "conclusion": "success", "head_sha": sha})
                if args[:3] == ["gh", "run", "download"]:
                    destination = Path(args[args.index("--dir") + 1])
                    (destination / "artifact.apk").write_bytes(b"fixture-apk")
                    return ""
                if args[:3] == ["git", "-C", str(root / "checkout")]:
                    return sha + "\n"
                if args == ["adb", "devices"]:
                    return "List of devices attached\nemulator-5554\tdevice\n"
                if args[:4] == ["adb", "-s", "emulator-5554", "install"]:
                    return "Success\n"
                if args[:6] == ["adb", "-s", "emulator-5554", "shell", "pm", "path"]:
                    package = args[6]
                    return f"package:/data/app/{package}/base.apk\n"
                if args[:5] == ["adb", "-s", "emulator-5554", "shell", "sha256sum"]:
                    path = args[5]
                    return hashlib.sha256(b"fixture-apk").hexdigest() + "  " + path + "\n"
                if args[0] == ci.sys.executable:
                    target = Path(args[args.index("--output") + 1])
                    target.write_text(json.dumps({"overall": "PASS_ONE_PRIVATE", "completed": 1,
                                                  "expected_cases": 1, "cases": {"a": "PASS"}}))
                    return ""
                raise AssertionError(args)
            with patch.object(ci, "command", side_effect=fake), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = ci.main(["--run-id", "123", "--serial", "emulator-5554",
                                "--checkout", str(root / "checkout"),
                                "--output-root", str(root / "reports"), "--test", "fixture"])
            self.assertEqual(code, 0)
            summary = json.loads(next((root / "reports").rglob("summary.json")).read_text())
            self.assertEqual(summary["overall"], "PASS_APK_PAIR_AND_SELECTED_TESTS")
            self.assertTrue(summary["installed_source_verified"])
            self.assertEqual(summary["tests"]["fixture"]["completed"], 1)
            self.assertFalse(summary["automatic_data_clear"])
            self.assertFalse(any(x[0] == "adb" and any(y in ("uninstall", "clear") for y in x) for x in commands))


if __name__ == "__main__":
    unittest.main()
