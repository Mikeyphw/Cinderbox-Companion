#!/usr/bin/env python3
"""UX09C02 HF03: bounded-readiness and diagnostics, fail-closed negative tests."""
from __future__ import annotations
import unittest
from ux09c02_hf03_fix import once,patch_android,patch_runner

ANDROID_ORIGINAL=b'''package com.sdvsync.ui.ux
import android.content.Context
class UxDeviceChromeTest {
    @Test fun voluntarySteamConnectionHasClearReturnToApp() {
        rule.onNodeWithTag("cinderbox.steam.connect").performClick()
        rule.onNodeWithTag("cinderbox.steam-login.screen").assertExists()
        rule.onNodeWithText("Connect your Steam account").assertExists()
        rule.onNodeWithText("Continue offline").assertDoesNotExist()
        rule.onNodeWithTag("cinderbox.steam-login.qr").assertExists()
        capture("steam", "cinderbox.steam-login.header")
        rule.onNodeWithTag("cinderbox.steam-login.back").performClick()
        rule.onNodeWithTag("cinderbox.screen.home").assertExists()
    }
performScrollToNode(hasTestTag("cinderbox.mods.advanced"))
}'''
RUNNER_ORIGINAL=b'''#!/usr/bin/env bash
UX09C02_PHYSICAL_DEVICE_REFUSED
svc wifi disable
svc data disable
UX09C02_INSTRUMENTATION_REFUSED
UX09C02_FAILURE.txt
grep -E 'FAILURES!!!|Test[s]? run:|Assertion|Exception|Error|INSTRUMENTATION_CODE|UX09C02_' "$logfile" | tail -60 >&2 || :
lines=[x[:250] for x in s.splitlines() if re.search(r'FAILURES!!!|Tests run:|AssertionError|UX09C02_|INSTRUMENTATION_CODE:',x)]
'''

class HF03Regression(unittest.TestCase):
 def test_exact_android_transform(self):
  t=patch_android(ANDROID_ORIGINAL).decode()
  self.assertEqual(t.count('private fun requireStage('),1)
  self.assertEqual(t.count('SystemClock.sleep(200L)'),1)
  self.assertIn('12_000L',t)
  self.assertIn('UX09C02_STAGE_FAILED:',t)
  self.assertIn('requireStage("steam-qr-action")',t)
  self.assertIn('requireStage("home-after-steam-back")',t)
  self.assertIn('"Continue offline").assertDoesNotExist()',t)
  self.assertIn('capture("steam", "cinderbox.steam-login.header")',t)
  self.assertIn('performScrollToNode(hasTestTag("cinderbox.mods.advanced"))',t)
 def test_no_soft_skip_in_auth_ui(self):
  t=patch_android(ANDROID_ORIGINAL).decode()
  self.assertNotIn('runCatching { rule.onNodeWithTag("cinderbox.steam-login.qr") }.getOrNull()',t)
  self.assertIn('rule.onNodeWithTag("cinderbox.steam-login.qr").assertExists()',t)
  self.assertIn('throw AssertionError("UX09C02_STAGE_FAILED:"',t)
 def test_android_rejects_missing_import(self):
  with self.assertRaisesRegex(AssertionError,'ANCHOR_COUNT'):
   patch_android(ANDROID_ORIGINAL.replace(b'import android.content.Context\n',b''))
 def test_android_rejects_missing_auth_check(self):
  with self.assertRaisesRegex(AssertionError,'ANCHOR_COUNT'):
   patch_android(ANDROID_ORIGINAL.replace(b'"Connect your Steam account"',b'"Steam login"'))
 def test_android_rejects_already_patched(self):
  with self.assertRaisesRegex(AssertionError,'ANCHOR_COUNT'):
   patch_android(patch_android(ANDROID_ORIGINAL))
 def test_runner_patch_preserves_hard_fail(self):
  r=patch_runner(RUNNER_ORIGINAL)
  self.assertIn(b'UX09C02_STAGE_',r)
  self.assertIn(b'UX09C02_INSTRUMENTATION_REFUSED',r)
  self.assertIn(b'UX09C02_PHYSICAL_DEVICE_REFUSED',r)
  self.assertIn(b'UX09C02_FAILURE.txt',r)
  self.assertIn(b'svc wifi disable',r)
  self.assertIn(b'Error in',r)
 def test_runner_rejects_missing_log_marker(self):
  with self.assertRaisesRegex(AssertionError,'ANCHOR_COUNT'):
   patch_runner(RUNNER_ORIGINAL.replace(b'INSTRUMENTATION_CODE|UX09C02_',b'INSTRUMENTATION_CODE'))
 def test_preimage_requires_single_unique_anchor(self):
  with self.assertRaisesRegex(AssertionError,'ANCHOR_COUNT'):
   once(b'aa',b'a',b'b','duplicate')
 def test_runner_fails_already_patched(self):
  with self.assertRaisesRegex(AssertionError,'ANCHOR_COUNT'):
   patch_runner(patch_runner(RUNNER_ORIGINAL))

if __name__=='__main__':unittest.main()
