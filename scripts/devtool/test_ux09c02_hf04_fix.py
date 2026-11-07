#!/usr/bin/env python3
"""UX09C02 HF04 scroll/visibility regression and fail-closed behavior."""
from __future__ import annotations
import unittest
from ux09c02_hf04_fix import once,patch_android,patch_workflow

ANDROID=b"""package com.sdvsync.ui.ux
import androidx.compose.ui.test.onNodeWithText
class UxDeviceChromeTest {
    @Test fun voluntarySteamConnectionHasClearReturnToApp() {
        requireStage("home-connect-action") {
            rule.onNodeWithTag("cinderbox.steam.connect").assertExists()
        }
        rule.onNodeWithTag("cinderbox.steam.connect").performClick()
        requireStage("steam-screen") {
            rule.onNodeWithTag("cinderbox.steam-login.screen").assertExists()
        }
        requireStage("steam-qr-action") {
            rule.onNodeWithTag("cinderbox.steam-login.qr").assertExists()
        }
        requireStage("steam-back-action") {
            rule.onNodeWithTag("cinderbox.steam-login.back").assertExists()
        }
        requireStage("home-after-steam-back") {
            rule.onNodeWithTag("cinderbox.screen.home").assertExists()
        }
        rule.onNodeWithText("Continue offline").assertDoesNotExist()
        capture("steam", "cinderbox.steam-login.header")
    }
performScrollToNode(hasTestTag("cinderbox.mods.advanced"))
}"""
WORKFLOW=b"""permissions:
  contents: read
jobs:
  source-contract:
    steps:
      - name: UI tests
        run: |
          python3 -B -m unittest discover -s scripts/devtool -p 'test_ux09c02_gate.py' -v
  hosted-api36-ui:
    steps:
      - name: Hosted app and test APK compile only
        run: ./gradlew :app:assembleDebugAndroidTest
      - name: Emulator
        with:
          api-level: 36
      - name: Upload
        if: always()
"""

class HF04Tests(unittest.TestCase):
 def test_positive_scroll_before_click(self):
  data=patch_android(ANDROID).decode()
  self.assertIn('performScrollTo()',data)
  self.assertIn('assertIsDisplayed()',data)
  self.assertIn('requireStage("home-connect-visible")',data)
  self.assertLess(data.index('performScrollTo()'),data.index('"cinderbox.steam.connect").performClick()'))
 def test_same_real_navigation_and_return(self):
  data=patch_android(ANDROID).decode()
  for tag in ('steam-screen','steam-qr-action','steam-back-action','home-after-steam-back'):
   self.assertIn('requireStage("'+tag+'")',data)
  self.assertIn('"Continue offline").assertDoesNotExist()',data)
 def test_no_fake_auth_or_direct_navigation(self):
  d=patch_android(ANDROID).decode()
  self.assertNotIn('navController.navigate(',d)
  self.assertNotIn('viewModel.login(',d)
  self.assertNotIn('runCatching {',d)
 def test_missing_click_refused(self):
  with self.assertRaisesRegex(AssertionError,'ANCHOR_MISMATCH'):
   patch_android(ANDROID.replace(b'.performClick()',b'.assertExists()'))
 def test_missing_semantics_refused(self):
  with self.assertRaisesRegex(AssertionError,'REQUIRED_SEMANTIC_LOST'):
   patch_android(ANDROID.replace(b'requireStage("steam-back-action")',b'requireStage("other")'))
 def test_duplicate_click_refused(self):
  mark=b'        rule.onNodeWithTag("cinderbox.steam.connect").performClick()\n'
  with self.assertRaisesRegex(AssertionError,'ANCHOR_MISMATCH'):
   patch_android(ANDROID.replace(mark,mark+mark))
 def test_patch_once(self):
  with self.assertRaisesRegex(AssertionError,'ANCHOR_MISMATCH'):
   patch_android(patch_android(ANDROID))
 def test_workflow_adds_source_regression(self):
  d=patch_workflow(WORKFLOW)
  self.assertIn(b"test_ux09c02_hf04_fix.py",d)
  self.assertIn(b':app:assembleDebugAndroidTest',d)
  self.assertIn(b'api-level: 36',d)
 def test_workflow_missing_gate_refused(self):
  with self.assertRaisesRegex(AssertionError,'ANCHOR_MISMATCH'):
   patch_workflow(WORKFLOW.replace(b'test_ux09c02_gate.py',b'test_other.py'))
 def test_workflow_double_patch_refused(self):
  with self.assertRaisesRegex(AssertionError,'ANCHOR_MISMATCH'):
   patch_workflow(patch_workflow(WORKFLOW))
 def test_unique_anchor(self):
  with self.assertRaisesRegex(AssertionError,'ANCHOR_MISMATCH'):
   once(b'xx',b'x',b'y','repeat')

if __name__=='__main__':unittest.main()
