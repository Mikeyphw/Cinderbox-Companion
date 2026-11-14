#!/usr/bin/env python3
"""LAB04 source mutation refusals and pure-policy Kotlin compile tests (not device evidence)."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import tempfile
import unittest

here=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab04_gate',here/'cbnx06_lab04_source_gate.py')
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class NegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=[gate.read(p) for p in (gate.STAGE,gate.POLICY,gate.PANEL,gate.UNIT,gate.WF,gate.FULL)]

    def test_positive(self):
        self.assertTrue(gate.validate(*self.data))

    def test_prod_capabilities_are_absent(self):
        for forbidden in ('getDownloadUrl(', 'ModDownloadService(', 'NexusPairingInbox.admit(',
                          'http://','https://','File("/storage','deleteRecursively('):
            self.assertNotIn(forbidden,self.data[0])

    def test_no_duplicate_ui_handlers(self):
        self.assertEqual(self.data[2].count('NexusLab04SyntheticTransaction.installSynthetic(context)'),1)
        self.assertEqual(self.data[2].count('NexusLab04SyntheticTransaction.rollbackSynthetic(context)'),1)


def add_negative(i,index,anchor):
    def test(self):
        entries=list(self.data)
        self.assertIn(anchor,entries[index])
        entries[index]=entries[index].replace(anchor,'LAB04_DELIBERATE_NEGATIVE_'+str(i),1)
        with self.assertRaises(gate.Refused):gate.validate(*entries)
    setattr(NegativeTests,f'test_refuse_mutation_{i:02}',test)

# >24 targeted corruptions; a single missing check makes the corresponding negative fail.
markers=[
  (0,'BuildConfig.CBNX_LAB && BuildConfig.APPLICATION_ID == APP'),
  (0,'context.packageName == APP'),
  (0,'CinderboxLabBoundary.requireModsRoot(mods)'),
  (0,'CinderboxLabBoundary.requirePrivate(journal)'),
  (0,'Files.isSymbolicLink(mods.toPath())'),
  (0,'Files.isSymbolicLink(journal.toPath())'),
  (0,'NexusLab03DArchiveStage.stageSynthetic(context)'),
  (0,'receipt.provenance == NexusLab03DArchivePolicy.PROVENANCE'),
  (0,'sha(archive.readBytes()) == receipt.sha256'),
  (0,'NexusLab04SyntheticPolicy.mayInstall('),
  (0,'review.changes.size == 1'),
  (0,'review.changes.single().action == "ADD"'),
  (0,'review.changes.single().folder == NexusLab04SyntheticPolicy.FOLDER'),
  (0,'review.changes.single().uniqueId == NexusLab04SyntheticPolicy.UNIQUE_ID'),
  (0,'manager.previewFromZip(archive)'),
  (0,'persist(journal, null, "INSTALLING", hash)'),
  (0,'manager.installFromZip(archive, review.approvalKey)'),
  (0,'check(exactSyntheticMod(mods))'),
  (0,'persist(journal, "INSTALLED", "ROLLING_BACK", hash)'),
  (0,'manager.removeMod(NexusLab04SyntheticPolicy.FOLDER)'),
  (0,'check(rootMembers(mods).isEmpty())'),
  (0,'persist(journal, "ROLLING_BACK", "ROLLED_BACK", hash)'),
  (0,'StandardCopyOption.ATOMIC_MOVE'),
  (0,'sha(manifest.readBytes()) == sha(MANIFEST.toByteArray(Charsets.UTF_8))'),
  (1,'!nexusVerified'),
  (1,'!productionFilesExamined'),
  (1,'existingState == null && emptyModsRoot'),
  (1,'existingState == "INSTALLED" && validInstalledBytes'),
  (2,'cbnx06.lab04.confirm-action'),
  (2,'NexusLab04SyntheticTransaction.rollbackSynthetic(context)'),
  (3,'@Test fun strictNonRecoverableCrashStates()'),
  (4,'persist-credentials: false'),
  (5,'python3 -B scripts/devtool/cbnx06_lab04_tests.py'),
]
for i,(index,anchor) in enumerate(markers,1):add_negative(i,index,anchor)

if __name__=='__main__':unittest.main(verbosity=2)
