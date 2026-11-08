#!/usr/bin/env python3
"""Mutation regressions for status-backed real UI error test. No Android tools."""
import json
from pathlib import Path
import shutil,tempfile,unittest
import nex_r3_hf02_gate as gate
FILES=(gate.TEST,gate.RUNNER,gate.WORKFLOW,gate.DOC,gate.POLICY)

class TestHF02Source(unittest.TestCase):
 def fixture(self,temp):
  root=Path(temp)
  for name in FILES:
   dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True)
   shutil.copyfile(gate.ROOT/name,dest)
  return root
 def mutate(self,name,needle,replacement,result):
  with tempfile.TemporaryDirectory() as t:
   root=self.fixture(t);p=root/name;s=p.read_text()
   self.assertIn(needle,s);p.write_text(s.replace(needle,replacement,1))
   self.assertIn(result,gate.check(root))
 def test_nominal(self):self.assertEqual([],gate.check())
 def test_status_not_recorded(self):
  self.mutate(gate.TEST,'responseCodes.add(code)','// removed', 'NEX_R3_HF02_MISSING:status recording')
 def test_no_status_wait(self):
  self.mutate(gate.TEST,'transport.responseCodes.contains(status)','true',
              'NEX_R3_HF02_MISSING:status-backed error UI')
 def test_no_lazy_scroll(self):
  self.mutate(gate.TEST,'.performScrollToNode(androidx.compose.ui.test.hasText("Mod catalog unavailable"))',
              '.performClick()','NEX_R3_HF02_MISSING:status-backed error UI')
 def test_no_visible_assert(self):
  self.mutate(gate.TEST,'compose.onNodeWithText("Mod catalog unavailable").assertIsDisplayed()',
              'compose.waitForIdle()','NEX_R3_HF02_MISSING:status-backed error UI')
 def test_missing_429_assertion(self):
  self.mutate(gate.TEST,'expectCatalogHttpFailure(429, "rate-429")','textVisible("Mod catalog unavailable")',
              'NEX_R3_HF02_MISSING:all 3 scenarios')
 def test_missing_503_assertion(self):
  self.mutate(gate.TEST,'expectCatalogHttpFailure(503, "server-503")','textVisible("Mod catalog unavailable")',
              'NEX_R3_HF02_MISSING:all 3 scenarios')
 def test_late_key_clear_is_not_accepted_as_prelaunch_isolation(self):
  self.mutate(gate.TEST, 'if (methodName.methodName != "noNexusKeyKeepsLocalModsRouteAvailable") {',
              'if (true) {', 'NEX_R3_HF02_MISSING:real no-key prelaunch')
 def test_missing_method_name_ordering(self):
  self.mutate(gate.TEST, 'RuleChain.outerRule(methodName).around(fixture).around(compose)',
              'RuleChain.outerRule(fixture).around(compose)',
              'NEX_R3_HF02_MISSING:real no-key prelaunch')
 def test_no_key_removed_before_prelaunch(self):
  self.mutate(gate.TEST, 'NEX_R3_NO_KEY_MUST_PRECEDE_ACTIVITY',
              'ALLOW_LATE_KEY_REMOVAL', 'NEX_R3_HF02_MISSING:real no-key prelaunch')
 def test_missing_per_viewport_reset(self):
  self.mutate(gate.RUNNER, 'pm clear com.sdvsync', 'pm list packages com.sdvsync',
              'NEX_R3_HF02_MISSING:per-viewport ephemerality')
 def test_reset_is_not_an_unconditional_host_command(self):
  self.mutate(gate.RUNNER, 'for width in 393 360; do', 'for screen in 393 360; do',
              'NEX_R3_HF02_MISSING:per-viewport ephemerality')
 def test_reset_refusal_is_fail_closed(self):
  self.mutate(gate.RUNNER, 'NEX_R3_EPHEMERAL_APP_DATA_RESET_REFUSED',
              'RESET_IGNORED', 'NEX_R3_HF02_MISSING:per-viewport ephemerality')
 def test_incomplete_runner_status(self):
  self.mutate(gate.RUNNER, 'HTTP_ERROR|HTTP_ERROR_UI', 'NO_HTTP_ERROR',
              'NEX_R3_HF02_MISSING:bounded coded diagnostics')
 def test_ci_must_run_negative_test(self):
  self.mutate(gate.WORKFLOW,'test_nex_r3_hf02_gate.py','nex_r3_skipped.py',
              'NEX_R3_HF02_MISSING:source gate hosted')
 def test_no_release_drift(self):
  with tempfile.TemporaryDirectory() as t:
   root=self.fixture(t);p=root/gate.POLICY;z=json.loads(p.read_text())
   z['release_enabled']=True;p.write_text(json.dumps(z))
   self.assertIn('NEX_R3_HF02_RELEASE_DRIFT:release_enabled',gate.check(root))
 def test_no_secrets(self):
  self.mutate(gate.TEST, 'NEX_R3_HTTP_ERROR_TIMEOUT:', 'CINDERBOX_NEXUS_API_KEY',
              'NEX_R3_HF02_UNSAFE:CINDERBOX_NEXUS_API_KEY')

if __name__=='__main__':unittest.main(verbosity=2)
