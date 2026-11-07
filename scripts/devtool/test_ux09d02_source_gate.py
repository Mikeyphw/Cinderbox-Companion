#!/usr/bin/env python3
"""Offline source-gate negative checks; no Gradle or network."""
import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from ux09d02_source_gate import ROOT,TEST,SHELL,REPORT,WORKFLOW,check

class SourceTests(unittest.TestCase):
    def test_real_checked_source(self):
        check()

    def test_missing_steam_route_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            for name in (TEST,SHELL,REPORT,WORKFLOW):
                dest=root/name
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes((ROOT/name).read_bytes())
            test=root/TEST
            test.write_text(test.read_text().replace('cinderbox.steam-login.screen','absent'))
            with self.assertRaises(AssertionError):
                check(root)

    def test_missing_emulator_guard_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            for name in (TEST,SHELL,REPORT,WORKFLOW):
                dest=root/name
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes((ROOT/name).read_bytes())
            sh=root/SHELL
            sh.write_text(sh.read_text().replace('ro.kernel.qemu','absent'))
            with self.assertRaises(AssertionError):
                check(root)

if __name__=='__main__':
    unittest.main()
