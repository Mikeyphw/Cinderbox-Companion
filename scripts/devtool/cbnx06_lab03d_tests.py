#!/usr/bin/env python3
"""Mutation negatives + reference ZIP fixtures. They do not substitute for Android execution."""
from __future__ import annotations
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[2]
GATE=ROOT/'scripts/devtool/cbnx06_lab03d_source_gate.py'
spec=importlib.util.spec_from_file_location('lab03d_gate', GATE)
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

def corpus():
    return [gate.read(path) for path in (gate.STAGE,gate.POLICY,gate.PANEL,
                                        gate.UNIT,gate.WF,gate.FULL)]

class MutationTests(unittest.TestCase):
    def test_original_contract(self):
        self.assertTrue(gate.validate(*corpus()))

    def test_adversarial_source_mutations(self):
        cases=[
            (0,'BuildConfig.CBNX_LAB && BuildConfig.APPLICATION_ID == APP','true'),
            (0,'context.packageName == APP','true'),
            (0,'CinderboxLabBoundary.requirePrivate(file)','Unit'),
            (0,'CinderboxLabBoundary.requireModsRoot(mods)','Unit'),
            (0,'NexusLab03Evidence.previewSynthetic(context)','null'),
            (0,'sourceReceipt.readText()','"{}"'),
            (0,'sourceHash == preview.archiveSha256','true'),
            (0,'saved.getString("source_sha256") == sourceHash','true'),
            (0,'digest(stage) == sourceHash','true'),
            (0,'LAB03D_PARTIAL_STAGE_REFUSED','REMOVED'),
            (0,'Files.isSymbolicLink(file.toPath())','false'),
            (0,'StandardCopyOption.ATOMIC_MOVE','StandardCopyOption.REPLACE_EXISTING'),
            (0,'check(!destination.exists())','true'),
            (0,'zip.nextEntry == null','true'),
            (0,'entry.name == NexusLab03DArchivePolicy.ENTRY','true'),
            (0,'CBNX06.LAB03.Synthetic','Wrong.UniqueID'),
            (0,'!previous.getBoolean("nexus_file_provenance_verified")','true'),
            (0,'.put("nexus_file_provenance_verified", false)','.put("nexus_file_provenance_verified", true)'),
            (0,'.put("installed", false)','.put("installed", true)'),
            (0,'.put("production_files_examined", false)','.put("production_files_examined", true)'),
            (0,'check(before == snapshot())','check(true)'),
            (0,'stage.exists() == receipt.exists()','true'),
            (1,'Regex("[0-9a-f]{64}")','Regex(".*")'),
            (1,'sourceSha256 == stagedSha256','true'),
            (1,'sourceBytes == stagedBytes','true'),
            (1,'!nexusVerified','true'),
            (1,'!installed','true'),
            (1,'!productionFilesExamined','true'),
            (2,'NexusLab03DArchiveStage.stageSynthetic(context)','unsafeCall(context)'),
            (2,'cbnx06.lab03d.stage-feedback','drifted-tag'),
            (3,'@Test fun refusesProvenanceEscalation()','@Test fun removed()'),
            (4,'python3 -B scripts/devtool/cbnx06_lab03d_tests.py','echo tests-skipped'),
            (5,'python3 -B scripts/devtool/cbnx06_lab03d_source_gate.py','echo not-run'),
        ]
        for index,original,replacement in cases:
            with self.subTest(index=index,anchor=original):
                fixture=corpus()
                self.assertIn(original,fixture[index])
                fixture[index]=fixture[index].replace(original,replacement,1)
                with self.assertRaisesRegex(gate.Refused,'LAB03D_'):
                    gate.validate(*fixture)

    def test_privileged_stage_surface_rejected(self):
        for suffix in ('\ngetDownloadUrl(\n','\nstartDownload(\n',
                       '\nModDownloadService(\n','\ninstallFromZip(\n',
                       '\nhttps://evil.invalid/\n','\nNexusPairingInbox.admit(\n'):
            with self.subTest(suffix=suffix):
                fixture=corpus();fixture[0]+=suffix
                with self.assertRaisesRegex(gate.Refused,'UNSAFE_STAGE_CAPABILITY'):
                    gate.validate(*fixture)

class ArchiveFixtureTests(unittest.TestCase):
    @staticmethod
    def make(entries):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            for name,raw in entries:
                z.writestr(name,raw)
        return out.getvalue()

    @staticmethod
    def inspect_fixture(data):
        # Reference fixture models source restrictions; JVM tests cover Kotlin policy.
        with zipfile.ZipFile(io.BytesIO(data),'r') as archive:
            names=archive.namelist()
            if names != ['CBNX06_LAB03_ONLY/manifest.json']:
                raise ValueError('LAB03D_REFERENCE_MEMBER_MISMATCH')
            info=archive.getinfo(names[0])
            if info.file_size > 4096:
                raise ValueError('LAB03D_REFERENCE_ENTRY_BUDGET')
            obj=json.loads(archive.read(info))
            if obj.get('UniqueID')!='CBNX06.LAB03.Synthetic' or obj.get('Version')!='1.0.0':
                raise ValueError('LAB03D_REFERENCE_MANIFEST_MISMATCH')

    def test_reference_positive_and_negative_archives(self):
        good=json.dumps({'UniqueID':'CBNX06.LAB03.Synthetic','Version':'1.0.0'}).encode()
        self.inspect_fixture(self.make([('CBNX06_LAB03_ONLY/manifest.json',good)]))
        cases=[
            [('other/manifest.json',good)],
            [('CBNX06_LAB03_ONLY/manifest.json',good),('extra',b'x')],
            [('CBNX06_LAB03_ONLY/manifest.json',b'{broken')],
            [('CBNX06_LAB03_ONLY/manifest.json',b'{}')],
            [('CBNX06_LAB03_ONLY/manifest.json',good+b'X'*5000)],
            [('CBNX06_LAB03_ONLY/manifest.json',json.dumps({'UniqueID':'Other','Version':'1.0.0'}).encode())],
            [('CBNX06_LAB03_ONLY/manifest.json',json.dumps({'UniqueID':'CBNX06.LAB03.Synthetic','Version':'2.0.0'}).encode())],
        ]
        for entries in cases:
            with self.subTest(entries=repr(entries)[:60]):
                with self.assertRaises(Exception):self.inspect_fixture(self.make(entries))

    def test_reference_byte_drift_and_partial_commit(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=root/'source.zip'; staged=root/'stage.zip';receipt=root/'receipt.json'
            content=self.make([('CBNX06_LAB03_ONLY/manifest.json',
                json.dumps({'UniqueID':'CBNX06.LAB03.Synthetic','Version':'1.0.0'}))])
            source.write_bytes(content);staged.write_bytes(content)
            import hashlib
            digest=lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest(source)==digest(staged)
            staged.write_bytes(content+b'changed')
            self.assertNotEqual(digest(source),digest(staged))
            self.assertTrue(staged.exists() != receipt.exists())

if __name__=='__main__':
    unittest.main(verbosity=2)
