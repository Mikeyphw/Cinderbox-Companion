#!/usr/bin/env python3
"""Adversarial LAB03C source tests; retain UI/bridge safety while deferred physical."""
from __future__ import annotations
from pathlib import Path
import tempfile,shutil,unittest
from cbnx06_lab03c_source_gate import validate,ROOT,Refused
PATHS={
  'policy':'app/src/main/java/com/sdvsync/mods/NexusLab03CPolicy.kt',
  'jvm':'app/src/test/java/com/sdvsync/mods/NexusLab03CPolicyTest.kt',
  'panel':'app/src/main/java/com/sdvsync/ui/screens/NexusPairingPanel.kt',
  'launcher':'app/src/main/java/com/sdvsync/mods/api/NexusBrowserLauncher.kt',
  'inbox':'app/src/main/java/com/sdvsync/mods/NexusPairingInbox.kt',
  'workflow':'.github/workflows/cbnx06-full-cinderbox-lab.yml',
  'hosted':'.github/workflows/cbnx06-lab03c-user-action.yml',
}
class Lab03CNegatives(unittest.TestCase):
    @classmethod
    def setUpClass(cls):validate(ROOT)
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='cbnx06-lab03c-neg-')
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        for path in PATHS.values():
            dst=self.root/path;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/path,dst)
    def refuse(self,key,old,new,reason):
        file=self.root/PATHS[key];text=file.read_text()
        self.assertEqual(text.count(old),1,old)
        file.write_text(text.replace(old,new,1))
        with self.assertRaisesRegex(Refused,reason):validate(self.root)
    def test_no_lab_package_guard(self):
        self.refuse('launcher','context.packageName != "com.sdvsync.cbnx06lab"',
                    'context.packageName == "com.sdvsync"','LAB_BROWSER_GUARD_MISSING')
    def test_no_real_browser_launch_result(self):
        self.refuse('panel','check(NexusBrowserLauncher.openLabFilePage(context, url))',
                    'NexusBrowserLauncher.openLabFilePage(context, url)','CONFIRMATION_OR_PRODUCTION_PARITY_LOST')
    def test_no_nxm_production_route(self):
        self.refuse('panel','NexusBrowserHandoff.createUrl(item.modId, item.fileId)',
                    'NexusBrowserHandoff.createUrl(item.modId, "999")','CONFIRMATION_OR_PRODUCTION_PARITY_LOST')
    def test_no_second_tap(self):
        self.refuse('panel','lab03cSelection = item // First tap only requests confirmation.',
                    'lab03cFeedback = null // unconfirmed','CONFIRMATION_OR_PRODUCTION_PARITY_LOST')
    def test_no_inbox_readback(self):
        self.refuse('panel','NexusPairingInbox.list(context).singleOrNull',
                    'inbox.singleOrNull','CONFIRMATION_OR_PRODUCTION_PARITY_LOST')
    def test_no_expiry_bound(self):
        self.refuse('policy','now - createdAt > MAX_REQUEST_AGE_MS',
                    'false','POLICY_ANCHOR_LOST')
    def test_no_identity_bound(self):
        self.refuse('policy','Regex("[1-9][0-9]{0,11}")','Regex(".*")',
                    'POLICY_ANCHOR_LOST')
    def test_no_fixed_https_site(self):
        self.refuse('policy','https://www.nexusmods.com/stardewvalley/mods/',
                    'http://example.invalid/stardewvalley/mods/', 'POLICY_ANCHOR_LOST')
    def test_no_pending_status_check(self):
        self.refuse('panel','it.fileId == selected.fileId && it.status == "PENDING"',
                    'it.fileId == selected.fileId','CONFIRMATION_OR_PRODUCTION_PARITY_LOST')
    def test_no_stale_commit(self):
        self.refuse('panel','NexusPairingInbox.resolve(context, current.id, "OPENED")',
                    'NexusPairingInbox.resolve(context, current.id, "DISMISSED")',
                    'CONFIRMATION_OR_PRODUCTION_PARITY_LOST')
    def test_no_lost_dismiss(self):
        self.refuse('panel','NexusPairingInbox.resolve(context, item.id, "DISMISSED")',
                    'NexusPairingInbox.resolve(context, item.id, "PENDING")',
                    'DISMISS_RECOVERY_REMOVED')
    def test_no_lost_full_lab_coverage(self):
        self.refuse('workflow','python3 -B scripts/devtool/cbnx06_lab03c_source_gate.py',
                    'python3 -B scripts/devtool/cbnx06_lab03b_source_gate.py',
                    'FULL_LAB_WORKFLOW_GATE_MISSING')
    def test_no_fake_browser_success(self):
        self.refuse('launcher','fun openLabFilePage(context: Context, url: String): Boolean',
                    'fun openLabFilePage(context: Context, url: String): Unit',
                    'LAB_BROWSER_GUARD_MISSING')
    def test_no_implicit_install(self):
        self.refuse('policy','return canonicalUrl(modId, fileId)',
                    'startDownload(modId); return canonicalUrl(modId, fileId)',
                    'POLICY_PRIVILEGE_LEAK')
    def test_no_missing_dedicated_ci(self):
        self.refuse('hosted',':app:testDebugUnitTest', ':app:assembleDebug',
                    'DEDICATED_CI_GATE_MISSING')
    def test_negative_source_no_physical_claim(self):
        # Invariant: hosted tests do not conflate request or browser launch with provider acceptance.
        s=(ROOT/PATHS['policy']).read_text()
        p=(ROOT/PATHS['panel']).read_text()
        self.assertNotIn('nxm://',s)
        self.assertIn('page, file, authorization and transfer remain unverified',p)
        self.assertIn('No download, archive or installation is authorized',p)

if __name__=='__main__':unittest.main(verbosity=2)
