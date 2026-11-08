#!/usr/bin/env python3
from __future__ import annotations
import shutil,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import nex_r5_gate

class R5SourceTests(unittest.TestCase):
    def test_real_contract(self):
        self.assertEqual([],nex_r5_gate.check())

    def test_negative_inert_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for relative in [nex_r5_gate.DETAIL,nex_r5_gate.HTML,nex_r5_gate.LEGACY,
                nex_r5_gate.LINKS,nex_r5_gate.VIEWMODEL,nex_r5_gate.TEST,nex_r5_gate.RUNNER,nex_r5_gate.CI,
                nex_r5_gate.POLICY,nex_r5_gate.PROBE,nex_r5_gate.PROBE_TEST,
                nex_r5_gate.SCHEMA_DOC,nex_r5_gate.SCHEMA_FUTURE]:
                file=root/relative;file.parent.mkdir(parents=True,exist_ok=True)
                file.write_bytes((nex_r5_gate.ROOT/relative).read_bytes())
            file=root/nex_r5_gate.LINKS
            file.write_text(file.read_text().replace('uri.port != -1', 'false'))
            self.assertIn('NEX_R5_MISSING:safe browser links',nex_r5_gate.check(root))

    def test_release_gate_remains_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for relative in [nex_r5_gate.DETAIL,nex_r5_gate.HTML,nex_r5_gate.LEGACY,
                nex_r5_gate.LINKS,nex_r5_gate.VIEWMODEL,nex_r5_gate.TEST,nex_r5_gate.RUNNER,nex_r5_gate.CI,
                nex_r5_gate.POLICY,nex_r5_gate.PROBE,nex_r5_gate.PROBE_TEST,
                nex_r5_gate.SCHEMA_DOC,nex_r5_gate.SCHEMA_FUTURE]:
                file=root/relative;file.parent.mkdir(parents=True,exist_ok=True)
                file.write_bytes((nex_r5_gate.ROOT/relative).read_bytes())
            file=root/nex_r5_gate.POLICY
            file.write_text(file.read_text().replace('"release_enabled": false', '"release_enabled": true'))
            self.assertIn('NEX_R5_RELEASE_GUARD:release_enabled',nex_r5_gate.check(root))

if __name__=='__main__':unittest.main()
