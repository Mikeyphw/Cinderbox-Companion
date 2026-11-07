#!/usr/bin/env python3
"""Offline positive/negative tests for UX09C02 HF02's exact source transformation."""
from __future__ import annotations
import unittest
from ux09c02_hf02_fix import (
    ANDROID_TEST, M4_TEST, PREIMAGES, once, patch_android, patch_m4,
)


class HF02Contracts(unittest.TestCase):
    def test_two_exact_source_files_only(self):
        self.assertEqual(set(PREIMAGES), {ANDROID_TEST, M4_TEST})
        for blob in PREIMAGES.values():
            self.assertRegex(blob, r'^[0-9a-f]{40}$')

    def test_reject_missing_anchor(self):
        with self.assertRaisesRegex(AssertionError, 'ANCHOR_COUNT'):
            once(b'other', b'absent', b'change', 'missing')

    def test_reject_duplicate_anchor(self):
        with self.assertRaisesRegex(AssertionError, 'ANCHOR_COUNT'):
            once(b'repeat repeat', b'repeat', b'fixed', 'duplicate')

    def test_reject_noop_replacement(self):
        with self.assertRaisesRegex(AssertionError, 'NOOP'):
            once(b'anchor', b'anchor', b'anchor', 'noop')

    def test_scroll_to_lazy_item_instead_of_child_scroll(self):
        src = (b'import androidx.compose.ui.test.performScrollTo\n'
               b'        rule.onNodeWithTag("cinderbox.mods.advanced").performScrollTo().performClick()\n')
        out = patch_android(src)
        self.assertIn(b'performScrollToNode(hasTestTag("cinderbox.mods.advanced"))', out)
        self.assertIn(b'onNodeWithTag("cinderbox.screen.mods")', out)
        self.assertIn(b'onNodeWithTag("cinderbox.mods.advanced").performClick()', out)
        self.assertNotIn(b'performScrollTo()', out)
        self.assertNotIn(b'import androidx.compose.ui.test.performScrollTo\n', out)

    def test_android_patch_refuses_wrong_import(self):
        with self.assertRaisesRegex(AssertionError, 'ANCHOR_COUNT'):
            patch_android(b'only sample')

    def test_android_patch_refuses_wrong_navigation(self):
        with self.assertRaisesRegex(AssertionError, 'ANCHOR_COUNT'):
            patch_android(b'import androidx.compose.ui.test.performScrollTo\n')

    def test_m4_preserves_explicit_offline_return(self):
        src=(b"        assert 'Continue offline' in login\n"
             b"        assert 'onContinueOffline' in login\n"
             b"        assert 'navController.navigate(\"main\")' in nav\n")
        out=patch_m4(src)
        for phrase in (b"assert 'Continue offline' not in login",
                       b'CinderboxSteamLoginHeader(onBack = onContinueOffline)',
                       b"assert 'onContinueOffline = {' in nav",
                       b"assert 'onOpenSettings = { navController.navigate(\\\"prelogin_settings\\\") }' in nav".replace(b'\\"', b'"')):
            self.assertIn(phrase, out)

    def test_m4_patch_refuses_duplicate(self):
        src=(b"        assert 'Continue offline' in login\n"
             b"        assert 'onContinueOffline' in login\n"
             b"        assert 'navController.navigate(\"main\")' in nav\n")
        with self.assertRaisesRegex(AssertionError, 'ANCHOR_COUNT'):
            patch_m4(src * 2)

    def test_m4_patch_refuses_unrelated_contract(self):
        with self.assertRaisesRegex(AssertionError, 'ANCHOR_COUNT'):
            patch_m4(b'assert unrelated')

    def test_no_production_security_or_auth_write_edits(self):
        self.assertNotIn('app/src/main', '\n'.join(PREIMAGES))
        results=patch_android(b'import androidx.compose.ui.test.performScrollTo\n'
                     b'        rule.onNodeWithTag("cinderbox.mods.advanced").performScrollTo().performClick()\n')
        for token in (b'restoreBackup(',b'deleteRecursively(',b'forceSync(',
                      b'viewModel.login(',b'LIVE_UPDATES_ENABLED = true',b'grantPermission('):
            self.assertNotIn(token,results)


if __name__=='__main__':unittest.main()
