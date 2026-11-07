#!/usr/bin/env python3
"""Fail-closed offline source regression for UX09C02 HF01."""
from __future__ import annotations
import unittest
from ux09c02_hf01_fix import PATCHES, replace_unique

class UX09C02HF01Tests(unittest.TestCase):
    def test_exact_two_preimages(self):
        self.assertEqual(len(PATCHES), 2)
        self.assertEqual(set(PATCHES), {
            'app/src/androidTest/java/com/sdvsync/ui/ux/UxDeviceChromeTest.kt',
            'app/src/main/java/com/sdvsync/ui/screens/LoginScreen.kt',
        })
        for sha, before, after in PATCHES.values():
            self.assertRegex(sha, r'^[0-9a-f]{40}$')
            self.assertTrue(before)
            self.assertNotEqual(before, after)
    def test_invalid_compose_import_removed(self):
        _, old, new = PATCHES['app/src/androidTest/java/com/sdvsync/ui/ux/UxDeviceChromeTest.kt']
        src = b'package sample\n' + old + b'import androidx.compose.ui.test.onNodeWithTag\n'
        result = replace_unique(src, old, new, 'androidtest')
        self.assertNotIn(old, result)
        self.assertIn(b'onNodeWithTag', result)
    def test_restore_localized_prelogin_settings_contract(self):
        _, old, new = PATCHES['app/src/main/java/com/sdvsync/ui/screens/LoginScreen.kt']
        src = b'onClick = onOpenSettings\n' + old + b'\n'
        result = replace_unique(src, old, new, 'login')
        self.assertIn(b'stringResource(R.string.settings_title)', result)
        self.assertIn(b'onClick = onOpenSettings', result)
    def test_missing_anchor_refused(self):
        with self.assertRaisesRegex(AssertionError, 'ANCHOR_COUNT'):
            replace_unique(b'other', b'missing', b'fixed', 'bad')
    def test_duplicate_anchor_refused(self):
        with self.assertRaisesRegex(AssertionError, 'ANCHOR_COUNT'):
            replace_unique(b'dup dup', b'dup', b'fixed', 'bad')
    def test_no_unauthorized_auth_or_mod_writes(self):
        changes = b'\n'.join(after for _,_,after in PATCHES.values())
        for forbidden in (b'loginWithQR(', b'authenticate(', b'forceSync(', b'restoreBackup(', b'deleteRecursively(', b'LIVE_UPDATES_ENABLED = true'):
            self.assertNotIn(forbidden, changes)

if __name__ == '__main__': unittest.main()
