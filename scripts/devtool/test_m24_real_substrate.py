"""No-device tests of M24 read-only installed CI APK pair provenance."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import m24_real_substrate as gate

SHA = "56976102313d857fd3971bdc64f1cf4752e6c751"
RUN = 39132432005
SERIAL = "emulator-5554"


class TestM24RealSubstrate(unittest.TestCase):
    def test_rejects_wrong_run_or_branch_or_incomplete(self):
        good = dict(id=RUN, head_sha=SHA, status="completed", conclusion="success",
                    head_branch=gate.EXPECTED_BRANCH, repository={"full_name": gate.REPO})
        gate.require_ci_identity(good, RUN, SHA)
        for key, bad in [("head_sha", "a" * 40), ("id", RUN+1),
                         ("head_branch", "master"), ("status", "in_progress"),
                         ("conclusion", "failure"), ("repository", {"full_name": "untrusted/repo"})]:
            with self.subTest(key=key), self.assertRaises(gate.ProofError):
                gate.require_ci_identity({**good, key: bad}, RUN, SHA)

    def test_strict_single_package_and_digest(self):
        path = "/data/app/~~opaque/com.sdvsync/base.apk"
        self.assertEqual(gate.parse_pm_path("package:"+path+"\n"), path)
        self.assertEqual(gate.parse_sha256sum("a"*64+"  "+path+"\n",path),"a"*64)
        for output in ["", "package:/sdcard/file.apk\n", "package:"+path+"\npackage:/data/app/extra/base.apk\n"]:
            with self.subTest(output=output), self.assertRaises(gate.ProofError):
                gate.parse_pm_path(output)
        for output in ["a"*63+"  "+path, "a"*64+"  /tmp/wrong.apk", "a"*64+"  "+path+"\nextra"]:
            with self.subTest(output=output), self.assertRaises(gate.ProofError):
                gate.parse_sha256sum(output,path)

    def test_only_one_apk_no_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"one.apk").write_bytes(b"a")
            self.assertEqual(gate.only_apk(root).name,"one.apk")
            (root/"two.apk").write_bytes(b"b")
            with self.assertRaises(gate.ProofError):gate.only_apk(root)

    def fake_tools(self, *, mismatch=False, cinderbox_visible=True):
        hashes={k:hashlib.sha256(k.encode()).hexdigest() for k in gate.ARTIFACTS}
        run = dict(id=RUN, head_sha=SHA, status="completed", conclusion="success",
                   head_branch=gate.EXPECTED_BRANCH, repository={"full_name": gate.REPO})
        def result(code=0, out=""):
            return subprocess.CompletedProcess([],code,out,"")
        def gh(argv):
            if argv[:2]==["gh","api"]:return result(out=json.dumps(run))
            assert argv[:3]==["gh","run","download"]
            name=argv[argv.index("--name")+1]
            folder=Path(argv[argv.index("--dir")+1])
            key=next(k for k,v in gate.ARTIFACTS.items() if v==name)
            (folder / (name+".apk")).write_bytes(key.encode())
            return result()
        def adb(argv):
            if argv==["adb","devices"]:return result(out="List of devices attached\nemulator-5554\tdevice\nlocalhost:5555\tdevice\n")
            assert argv[:4]==["adb","-s",SERIAL,"shell"]
            if argv[4:6]==["pm","path"]:
                package=argv[6]
                if package=="com.game.cinderbox":return result(out="package:/data/app/cinderbox/base.apk\n")
                return result(out=f"package:/data/app/{package}/base.apk\n")
            if argv[4]=="sha256sum":
                path=argv[5]
                key=next(k for k,p in gate.PACKAGES.items() if f"/{p}/base.apk" == path[len("/data/app"):])
                digest="0"*64 if mismatch and key=="test" else hashes[key]
                return result(out=f"{digest}  {path}\n")
            if argv[4:6]==["test","-d"]:
                return result(0 if cinderbox_visible else 1)
            raise AssertionError(argv)
        return gh,adb

    def test_success_attests_only_apks_not_game(self):
        result=gate.inspect(*self.fake_tools(),RUN,SHA,SERIAL)
        self.assertEqual(result["overall"],"PASS_CI_INSTALLED_APK_PAIR_BYTE_MATCH_READ_ONLY")
        self.assertTrue(result["installed_source_verified"])
        self.assertTrue(result["imported_cinderbox_inspected"])
        for negative in ("signed_depot_manifest_verified", "steam_entitlement_verified",
                         "authenticated_steam_tested", "real_download_performed", "device_qualified",
                         "game_files_modified", "automatic_install", "publication_allowed"):
            self.assertFalse(result[negative],negative)

    def test_mismatch_and_missing_cinderbox_do_not_escalate(self):
        with self.assertRaisesRegex(gate.ProofError,"INSTALLED_APK_BYTES_DIFFER_FROM_CI"):
            gate.inspect(*self.fake_tools(mismatch=True),RUN,SHA,SERIAL)
        result=gate.inspect(*self.fake_tools(cinderbox_visible=False),RUN,SHA,SERIAL)
        self.assertTrue(result["installed_source_verified"])
        self.assertEqual(result["cinderbox_paths"]["game"],"NOT_OBSERVED_OR_INACCESSIBLE")

    def test_no_device_or_install_mutations_in_source(self):
        source=Path(gate.__file__).read_text()
        self.assertNotIn('"install",',source)
        self.assertNotIn('"uninstall",',source)
        self.assertNotIn('"clear",',source)
        self.assertNotIn('"su",',source)
        self.assertNotIn('"reboot",',source)
        self.assertNotIn('"am", "force-stop"',source)

if __name__ == "__main__": unittest.main()
