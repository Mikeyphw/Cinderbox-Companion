#!/usr/bin/env python3
"""Negative checks verify the source gate refuses each critical omission."""
import json, pathlib, shutil, tempfile, unittest
import nex_r4_gate as gate

FILES=(gate.SCREEN,gate.ANDROID,gate.RUNNER,gate.EVIDENCE,gate.WORKFLOW,gate.DOC,gate.POLICY)

class NexR4SourceTest(unittest.TestCase):
    def fixture(self,folder):
        root=pathlib.Path(folder)
        for f in FILES:
            out=root/f;out.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(gate.ROOT/f,out)
        return root
    def tamper(self,path,old,new,expected):
        with tempfile.TemporaryDirectory() as t:
            root=self.fixture(t);p=root/path;s=p.read_text()
            self.assertIn(old,s)
            p.write_text(s.replace(old,new,1))
            self.assertIn(expected,gate.check(root))
    def test_nominal(self): self.assertEqual([],gate.check())
    def test_no_offline_sheet(self):
        self.tamper(gate.SCREEN,'nex.r4.offline-saved-detail','removed','NEX_R4_MISSING:local saved detail only')
    def test_no_key_bypass(self):
        self.tamper(gate.SCREEN,'if (filter == DiscoverFilter.SAVED && !browse.hasApiKey)',
            'if (false)', 'NEX_R4_MISSING:remote detail guarded')
    def test_bad_image_load(self):
        self.tamper(gate.SCREEN,'if (!offlineMetadataOnly && !mod.pictureUrl.isNullOrBlank())',
            'if (!mod.pictureUrl.isNullOrBlank())','NEX_R4_MISSING:no offline image HTTP')
    def test_fake_compose_rule(self):
        self.tamper(gate.ANDROID,'createAndroidComposeRule<MainActivity>()',
            'createComposeRule()', 'NEX_R4_MISSING:real activity and isolated fixture')
    def test_remove_network_counter(self):
        self.tamper(gate.ANDROID,'NEX_R4_REFUSED_PROVIDER_CALL',
            'REMOVED', 'NEX_R4_MISSING:real activity and isolated fixture')
    def test_missing_offline_runner(self):
        self.tamper(gate.RUNNER,'r48_offline_gate.py','removed',
            'NEX_R4_MISSING:offline-only CI and device identity')
    def test_remote_device_guard(self):
        self.tamper(gate.RUNNER,'ro.kernel.qemu','removed',
            'NEX_R4_MISSING:offline-only CI and device identity')
    def test_missing_android_workflow(self):
        self.tamper(gate.WORKFLOW,'assembleDebugAndroidTest','omitted',
            'NEX_R4_MISSING:hosted real activity CI')
    def test_release_unchanged(self):
        with tempfile.TemporaryDirectory() as t:
            root=self.fixture(t);p=root/gate.POLICY
            policy=json.loads(p.read_text());policy['publication_enabled']=True
            p.write_text(json.dumps(policy))
            self.assertIn('NEX_R4_RELEASE_POLICY_CHANGED:publication_enabled',gate.check(root))
    def test_forbid_install(self):
        self.tamper(gate.ANDROID,'NEX_R4_REAL_MAIN_ACTIVITY_SAVED_OFFLINE_PASS',
            'installFile(', 'NEX_R4_UNSAFE:installFile(')

if __name__=='__main__': unittest.main(verbosity=2)
