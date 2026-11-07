"""Offline negative tests for the Nexus-native source contract."""
import unittest
from unittest.mock import patch
import nex_r1_gate as gate

class NexR1GateTests(unittest.TestCase):
    def test_real_checked_source(self):
        result=gate.check()
        self.assertTrue(result['server_filter_and_sort'])
        self.assertFalse(result['webview'])
    def test_refuse_local_only_filter(self):
        file='app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt'
        original=gate.source
        def tainted(path,root=gate.ROOT):
            data=original(path,root)
            return data+'\n// categoryName == mod.categoryName\n' if path==file else data
        with patch.object(gate,'source',side_effect=tainted):
            with self.assertRaisesRegex(AssertionError,'NEX_R1_LOCAL_CATEGORY_FILTER_NOT_REMOVED'):
                gate.check()
    def test_refuse_unsafe_install(self):
        file='app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt'
        original=gate.source
        def tainted(path,root=gate.ROOT):
            data=original(path,root)
            return data+'\n// installMod(\n' if path==file else data
        with patch.object(gate,'source',side_effect=tainted):
            with self.assertRaisesRegex(AssertionError,'NEX_R1_UNSAFE_OPERATION_IN_BROWSE'):
                gate.check()
    def test_refuse_unauthorised_release(self):
        file='docs/security/M3_RELEASE_POLICY.json'
        original=gate.source
        def tainted(path,root=gate.ROOT):
            data=original(path,root)
            return data.replace('"release_enabled": false','"release_enabled": true') if path==file else data
        with patch.object(gate,'source',side_effect=tainted):
            with self.assertRaisesRegex(AssertionError,'NEX_R1_RELEASE_GATE_CHANGED'):
                gate.check()

if __name__=='__main__':unittest.main()
