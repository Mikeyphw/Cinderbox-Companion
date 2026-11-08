#!/usr/bin/env python3
"""Negative and positive regression checks for HF01 (no Android Gradle)."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import nex_r3_hf01_gate as gate

FILES=(gate.TEST,gate.RUNNER,gate.WORKFLOW,gate.POLICY)
class SourceDiagnosticsTest(unittest.TestCase):
    def fixture(self,root):
        root=Path(root)
        for name in FILES:
            dst=root/name
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(gate.ROOT/name,dst)
        return root
    def tamper(self,name,old,new,expected):
        with tempfile.TemporaryDirectory() as t:
            root=self.fixture(t);p=root/name;data=p.read_text()
            self.assertIn(old,data)
            p.write_text(data.replace(old,new,1))
            self.assertIn(expected,gate.check(root))
    def test_real_postimage_passes(self): self.assertEqual([],gate.check())
    def test_old_fixture_only_rule_is_rejected(self):
        self.tamper(gate.TEST,
                    'RuleChain.outerRule(methodName).around(fixture).around(compose)',
                    'RuleChain.outerRule(fixture).around(compose)',
                    'NEX_R3_HF01_MISSING:real tests retained')
    def test_no_key_selector_must_run_before_activity(self):
        self.tamper(gate.TEST,
                    'if (methodName.methodName != "noNexusKeyKeepsLocalModsRouteAvailable") {',
                    'if (true) {',
                    'NEX_R3_HF01_MISSING:no-key prelaunch rule isolation')
    def test_no_key_prelaunch_assertion_cannot_disappear(self):
        self.tamper(gate.TEST,'NEX_R3_NO_KEY_MUST_PRECEDE_ACTIVITY',
                    'NO_KEY_LATE_ONLY',
                    'NEX_R3_HF01_MISSING:no-key prelaunch rule isolation')
    def test_testname_rule_is_required(self):
        self.tamper(gate.TEST,'private val methodName = TestName()',
                    'private val methodName = "missing"',
                    'NEX_R3_HF01_MISSING:no-key prelaunch rule isolation')
    def test_missing_timeout_diagnostic_refused(self):
        self.tamper(gate.TEST,'NEX_R3_TEXT_TIMEOUT:','removed:', 'NEX_R3_HF01_MISSING:named text wait')
    def test_missing_tag_stage_refused(self):
        self.tamper(gate.TEST,'NEX_R3_TAG_TIMEOUT:','removed:', 'NEX_R3_HF01_MISSING:named tag wait')
    def test_missing_offset_stage_refused(self):
        self.tamper(gate.TEST,'NEX_R3_OFFSET_TIMEOUT:','removed:', 'NEX_R3_HF01_MISSING:named offset wait')
    def test_no_diag_file_refused(self):
        self.tamper(gate.RUNNER,'diagnostic-$width.txt','missing.txt','NEX_R3_HF01_MISSING:sanitized diagnostics')
    def test_missing_offline_gate_refused(self):
        self.tamper(gate.RUNNER,'r48_offline_gate.py','deleted_gate.py','NEX_R3_HF01_MISSING:offline and source pin')
    def test_no_release_policy_drift(self):
        with tempfile.TemporaryDirectory() as t:
            root=self.fixture(t);p=root/gate.POLICY;data=json.loads(p.read_text())
            data['release_enabled']=True;p.write_text(json.dumps(data))
            self.assertIn('NEX_R3_HF01_RELEASE_POLICY_CHANGED:release_enabled',gate.check(root))
    def test_cannot_reference_real_secret(self):
        self.tamper(gate.RUNNER,'NEX_R3_HOSTED_INSTRUMENTATION_REFUSED', 'CINDERBOX_NEXUS_API_KEY',
                    'NEX_R3_HF01_FORBIDDEN:CINDERBOX_NEXUS_API_KEY')
    def test_ci_cannot_drop_negative_gate(self):
        self.tamper(gate.WORKFLOW, "test_nex_r3_hf01_gate.py",'removed_hf01_tests.py',
                    'NEX_R3_HF01_MISSING:CI source checks')

if __name__=='__main__':unittest.main(verbosity=2)
