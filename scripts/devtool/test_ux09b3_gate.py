#!/usr/bin/env python3
"""Negative, fully offline tests for UX09B3 source contract and safety invariants."""
from __future__ import annotations
import hashlib,json,tempfile,unittest
from pathlib import Path
from ux09b3_gate import ROOT,FILES,check

class UX09B3SourceGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='ux09b3-gate-')
        self.root=Path(self.tmp.name)
        for name in FILES:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
            src=ROOT/name
            if src.is_file():p.write_bytes(src.read_bytes())
            else:
                # Only for isolated offline tests before production checkout applies.
                stub= {
                  FILES[7]: 'val permitsLiveBulkWrite: Boolean = false\n',
                  FILES[8]: 'const val LIVE_UPDATES_ENABLED: Boolean = false\nconst val DEVICE_ACCEPTED: Boolean = false\n',
                  FILES[9]: 'fun ApprovedGameScreen() {}\n',
                  FILES[10]:'fun ApprovedSavesScreen() {}\n',
                  FILES[11]:'fun ApprovedModDetailContent() {}\n',
                  FILES[6]:json.dumps({k:False for k in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete')}),
                  FILES[4]:'', FILES[5]:json.dumps([{'screen':i,'viewport':[393,852]} for i in range(24)])
                }.get(name,'')
                if name==FILES[4]:
                    html=b'local-fixture-reference\n'
                    ref=self.root/'design/cinderbox/01_REFERENCE/frozen.html'
                    ref.parent.mkdir(parents=True,exist_ok=True);ref.write_bytes(html)
                    stub=json.dumps({'reference':{'path':'01_REFERENCE/frozen.html','sha256':hashlib.sha256(html).hexdigest(),'sole_theme':'dark'},'screenshot_cases':{'count':24}})
                p.write_text(stub)
        contract=json.loads((self.root/FILES[4]).read_text())
        ref=self.root/'design/cinderbox'/contract['reference']['path']
        if not ref.exists():
            # When running inside the real checkout, the reference exists but
            # must also be copied to the standalone test fixture.
            original=ROOT/'design/cinderbox'/contract['reference']['path']
            ref.parent.mkdir(parents=True,exist_ok=True);ref.write_bytes(original.read_bytes())
    def tearDown(self):self.tmp.cleanup()
    def test_valid_test_only_contract(self):
        self.assertEqual(check(self.root)['result'],'UX09B3_PRESENTATION_FIXTURE_SOURCE_PASS')
    def test_unsafe_operation_is_refused(self):
        p=self.root/FILES[0];p.write_text(p.read_text()+'\n// startDownload( forbidden\n')
        with self.assertRaisesRegex(AssertionError,'UNSAFE_INSTRUMENTATION'):check(self.root)
    def test_steam_entitlement_claim_requires_false(self):
        p=self.root/FILES[0];p.write_text(p.read_text().replace('.put("real_steam_entitlement", false)', '.put("real_steam_entitlement", true)'))
        with self.assertRaisesRegex(AssertionError,'FALSE_EVIDENCE_MISSING'):check(self.root)
    def test_release_enabled_is_refused(self):
        p=self.root/FILES[6];v=json.loads(p.read_text());v['publication_enabled']=True;p.write_text(json.dumps(v))
        with self.assertRaisesRegex(AssertionError,'RELEASE_POLICY_DRIFT'):check(self.root)
    def test_browser_reference_drift_refused(self):
        v=json.loads((self.root/FILES[4]).read_text())
        p=self.root/'design/cinderbox'/v['reference']['path'];p.write_text('drift')
        with self.assertRaisesRegex(AssertionError,'APPROVED_REFERENCE_DRIFT'):check(self.root)

if __name__=='__main__':unittest.main()
