"""Host-only UX08B policy tests; no real Android, game files, or user identity."""
import json
import tempfile
import unittest
from pathlib import Path
import ux08b_gate

class UX08BPolicyTests(unittest.TestCase):
    def test_existing_source_and_privilege_gate(self):
        result=ux08b_gate.check()
        self.assertEqual(result['new_native_screens'],3)
        self.assertFalse(result['privileged_writes_from_new_screens'])
        self.assertFalse(result['release_enabled'])

    def test_screen_has_no_mutating_service_calls(self):
        src=ux08b_gate.source('app/src/main/java/com/sdvsync/ui/screens/ApprovedDeepToolsScreen.kt')
        for call in ('startDownload(', 'applyProfile(', 'extractSmapi(', 'deleteProfile('):
            self.assertNotIn(call,src)

    def test_profile_lookup_does_not_fall_back_to_display_name(self):
        src=ux08b_gate.source('app/src/main/java/com/sdvsync/ui/screens/ApprovedDeepToolsScreen.kt')
        self.assertIn('it.id == profileId',src)
        self.assertIn('matches.singleOrNull()',src)
        self.assertNotIn('firstOrNull { it.name',src)

    def test_release_flags_are_false(self):
        p=json.loads(ux08b_gate.source('docs/security/M3_RELEASE_POLICY.json'))
        for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
            self.assertIs(p[key],False)

if __name__=='__main__':unittest.main()
