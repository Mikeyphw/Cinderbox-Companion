import unittest
from unittest.mock import patch
import ux08a_gate as gate

class UX08ADeepContract(unittest.TestCase):
    def test_source_navigation_and_release_guards(self):
        result=gate.check()
        self.assertEqual(result['native_deep_screens'],2)
        self.assertFalse(result['permissions_requested_by_navigation'])
        self.assertFalse(result['publication_allowed'])
    def test_missing_queue_route_is_rejected(self):
        original=gate.source
        def broken(relative,root=gate.ROOT):
            text=original(relative,root)
            if relative.endswith('/MainActivity.kt'):
                return text.replace('composable("download_queue")','composable("download_disabled")')
            return text
        with patch.object(gate,'source',side_effect=broken):
            with self.assertRaises(AssertionError):gate.check()
    def test_privileged_action_leak_is_rejected(self):
        original=gate.source
        def broken(relative,root=gate.ROOT):
            text=original(relative,root)
            if relative.endswith('/ApprovedDeepStatusScreen.kt'):
                return text+'\n// startDownload( forbidden here\n'
            return text
        with patch.object(gate,'source',side_effect=broken):
            with self.assertRaises(AssertionError):gate.check()
    def test_security_policy_flags_are_required_false(self):
        original=gate.source
        def broken(relative,root=gate.ROOT):
            if relative=='docs/security/M3_RELEASE_POLICY.json':
                import json
                data=json.loads(original(relative,root));data['release_enabled']=True
                return json.dumps(data)
            return original(relative,root)
        with patch.object(gate,'source',side_effect=broken):
            with self.assertRaises(AssertionError):gate.check()
