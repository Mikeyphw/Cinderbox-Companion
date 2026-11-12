#!/usr/bin/env python3
"""LAB03B UX09 source mutation regressions: no emulator, no device access."""
from __future__ import annotations
from pathlib import Path
import unittest
from cbnx06_lab03b_ux09_gate import ROOT, PANEL, verify, Refused

class PairingUxGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src=(ROOT/PANEL).read_text()
        verify(cls.src)
    def refuse(self,old,new):
        self.assertEqual(self.src.count(old),1)
        with self.assertRaises(Refused):verify(self.src.replace(old,new,1))
    def test_disabled_before_pairing(self):
        self.assertIn('if (BuildConfig.CBNX_LAB || state.connected)',self.src)
        self.assertIn('enabled = state.connected && state.listening',self.src)
    def test_production_still_requires_pairing_to_show_switch(self):
        self.assertIn('BuildConfig.CBNX_LAB || state.connected',self.src)
    def test_consent_cannot_be_enabled_unpaired(self):
        self.refuse('enabled = state.connected && state.listening','enabled = true')
    def test_unpaired_must_render_switch_disabled(self):
        self.refuse('checked = state.connected && state.handoffEnabled', 'checked = true')
    def test_handler_rechecks_connected(self):
        self.refuse('if (state.connected && state.listening) {', 'if (true) {')
    def test_native_switch_only_once(self):
        with self.assertRaises(Refused):verify(self.src + '\nNexusPairingBridge.setHandoffEnabled(it)\n')
    def test_missing_status_refused(self):
        self.refuse('cbnx06.lab.pairing-status','missing-tag')
    def test_missing_discoverable_control_refused(self):
        self.refuse('if (BuildConfig.CBNX_LAB || state.connected)','if (state.connected)')
    def test_pairing_no_downloading_automatically(self):
        self.assertNotIn('getDownloadUrl(',self.src)
        self.assertNotIn('ModDownloadService.start(',self.src)
    def test_no_privileged_ownership_leak(self):
        self.assertNotIn('android.permission.MANAGE_EXTERNAL_STORAGE',self.src)

if __name__=='__main__':unittest.main(verbosity=2)
