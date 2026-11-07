#!/usr/bin/env python3
"""UX-09B4 source and visual receipt negative regression tests (offline)."""
from __future__ import annotations
import json,shutil,tempfile,unittest
from pathlib import Path
from ux09b4_gate import ROOT,REQUIRED,check
from ux09b4_visual_audit import analyze

class SourceGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ux09b4-src-')
        self.root=Path(self.temp.name)
        for name in REQUIRED:
            source=ROOT/name;target=self.root/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
        contract=json.loads((self.root/REQUIRED[6]).read_text())
        ref=Path('design/cinderbox')/contract['reference']['path']
        (self.root/ref).parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/ref,self.root/ref)
    def tearDown(self):self.temp.cleanup()
    def edit(self,path,old,new):
        p=self.root/path;s=p.read_text();self.assertIn(old,s);p.write_text(s.replace(old,new,1))
    def test_contract_passes(self):self.assertEqual(check(self.root)['result'],'UX09B4_SOURCE_AND_STATUS_INSET_PASS')
    def test_rejects_no_status_inset(self):
        self.edit(REQUIRED[0],'windowInsetsPadding(WindowInsets.statusBars)','windowInsetsPadding(WindowInsets(0, 0, 0, 0))')
        with self.assertRaisesRegex(AssertionError,'STATUS_INSETS'):check(self.root)
    def test_rejects_unwired_visual_audit(self):
        self.edit(REQUIRED[1],'python3 -B scripts/devtool/ux09b4_visual_audit.py', 'echo skip')
        with self.assertRaises(AssertionError):check(self.root)
    def test_rejects_mutable_browser_reference(self):
        c=json.loads((self.root/REQUIRED[6]).read_text());p=self.root/'design/cinderbox'/c['reference']['path']
        p.write_bytes(p.read_bytes()+b'x')
        with self.assertRaisesRegex(AssertionError,'REFERENCE_DRIFT'):check(self.root)
    def test_rejects_release_gate(self):
        p=self.root/REQUIRED[8];policy=json.loads(p.read_text());policy['release_enabled']=True
        p.write_text(json.dumps(policy))
        with self.assertRaisesRegex(AssertionError,'RELEASE_POLICY_DRIFT'):check(self.root)
    def test_rejects_fake_parity(self):
        self.edit(REQUIRED[3],"'native_goldens_approved':False", "'native_goldens_approved':True")
        with self.assertRaisesRegex(AssertionError,'FALSE_CLAIM'):check(self.root)

if __name__=='__main__':unittest.main()
