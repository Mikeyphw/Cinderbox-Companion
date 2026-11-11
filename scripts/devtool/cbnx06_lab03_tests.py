#!/usr/bin/env python3
"""LAB03A source mutation and redacted receipt negatives; no Android access."""
import tempfile,shutil,unittest
from pathlib import Path
from cbnx06_lab03_source_gate import ROOT,check,Refused
from cbnx06_lab03_receipt import verify
FILES={
'evidence':'app/src/main/java/com/sdvsync/mods/NexusLab03Evidence.kt',
'ui':'app/src/main/java/com/sdvsync/ui/screens/NexusPairingPanel.kt',
'test':'app/src/androidTest/java/com/sdvsync/mods/CbNxLab03DeviceTest.kt',
'gradle':'app/build.gradle.kts','runner':'scripts/devtool/cbnx06_lab03_emulator_ci.sh',
'receipt':'scripts/devtool/cbnx06_lab03_receipt.py',
'workflow':'.github/workflows/cbnx06-lab03-synthetic.yml'}
class Negatives(unittest.TestCase):
    @classmethod
    def setUpClass(cls):check(ROOT)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cbnx06-lab03a-neg-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for path in FILES.values():
            dest=self.root/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/path,dest)
    def mutate(self,key,old,new,reason):
        p=self.root/FILES[key];s=p.read_text();self.assertEqual(s.count(old),1,old)
        p.write_text(s.replace(old,new,1))
        with self.assertRaisesRegex(Refused,reason):check(self.root)
    def test_no_package_guard(self):self.mutate('evidence','BuildConfig.CBNX_LAB && context.packageName == LAB_PACKAGE','true','EVIDENCE_GUARD_MISSING')
    def test_no_private_boundary(self):self.mutate('evidence','CinderboxLabBoundary.requirePrivate(archiveFile)','// removed','EVIDENCE_GUARD_MISSING')
    def test_no_mod_boundary(self):self.mutate('evidence','CinderboxLabBoundary.requireModsRoot(mods)','// removed','EVIDENCE_GUARD_MISSING')
    def test_no_preview(self):self.mutate('evidence','ModFileManager(context, ModManifestParser()).previewFromZip(archiveFile)','ModArchivePreview()','EVIDENCE_GUARD_MISSING')
    def test_no_witness(self):self.mutate('evidence','check(before == after) { "LAB03_PREVIEW_MUTATED_MODS" }','// unchecked','EVIDENCE_GUARD_MISSING')
    def test_no_archive_durability_witness(self):self.mutate('evidence','LAB03_ARCHIVE_DURABILITY_MISMATCH','LAB03_WEAK_ARCHIVE_CHECK','EVIDENCE_GUARD_MISSING')
    def test_forbidden_download(self):self.mutate('evidence','private fun archive(): ByteArray {','private fun archive(): ByteArray {\n        ModDownloadService.start(','SYNTHETIC_CAPABILITY_FORBIDDEN')
    def test_fake_provider_claim(self):self.mutate('evidence','.put("nexus_file_provenance_verified", false)','.put("nexus_file_provenance_verified", true)','EVIDENCE_GUARD_MISSING')
    def test_ui_lab_guard(self):self.mutate('ui','if (BuildConfig.CBNX_LAB) {\n            Text("LAB03A synthetic only','if (true) {\n            Text("LAB03A synthetic only','UI_SYNTHETIC_BRANCH_UNGUARDED')
    def test_gradle_test_variant(self):self.mutate('gradle','-PcbnxLabAndroidTest=true','-PdebugLab=true','NO_ANCHOR') if False else self.mutate('gradle','if (providers.gradleProperty("cbnxLabAndroidTest").orNull == "true") "cbnxLab" else "debug"','"debug"','TEST_BUILD_VARIANT_MISSING')
    def test_ci_test_task(self):self.mutate('workflow',':app:assembleCbnxLabAndroidTest',':app:assembleDebugAndroidTest','HOSTED_GATE_MISSING')
    def test_android_test_roster(self):self.mutate('test','@Test fun labPairingRequiresConsentAndRecordsOnlyExactInboxRequest()','@Test fun skippedPairing()','DEVICE_COVERAGE_MISSING')
    def test_invalid_copied_archive_check_refused(self):
        self.mutate('test',
            '        val mods = File(CinderboxPaths.MODS_DIR)',
            '        check(archiveFile.isFile && sha256(archiveFile.readBytes()) == digest)\n'
            '        val mods = File(CinderboxPaths.MODS_DIR)',
            'LAB03A_HF01_UNBOUND_KOTLIN_ARCHIVE_LOCALS')
    def test_missing_synthetic_worker_build_source_refused(self):
        self.mutate('gradle',
            'getByName("cbnxLab").java.srcDir("src/debug/java")',
            'getByName("cbnxLab").java.srcDir("src/none/java")',
            'LAB03A_HF01_INHERITED_DEBUG_SYNTHETIC_WORKER_NOT_SHARED')
    def test_raw_log_not_proof(self):
        s='INSTRUMENTATION_STATUS: test=syntheticArchivePreviewDoesNotModifyLabMods\nOK (2 tests)\nINSTRUMENTATION_CODE: 0'
        r=verify(s,0,'a'*40,'123','b'*64,'c'*64)
        self.assertEqual(r['status'],'NOT_QUALIFIED')
        self.assertFalse(r['physical_qualified'])
    def test_success_without_production_evidence(self):
        names='INSTRUMENTATION_STATUS: test=syntheticArchivePreviewDoesNotModifyLabMods\nINSTRUMENTATION_STATUS: test=syntheticArchivePreviewDoesNotModifyLabMods\nINSTRUMENTATION_STATUS: test=labPairingRequiresConsentAndRecordsOnlyExactInboxRequest\nINSTRUMENTATION_STATUS: test=labPairingRequiresConsentAndRecordsOnlyExactInboxRequest\nOK (2 tests)\nINSTRUMENTATION_CODE: 0'
        r=verify(names,0,'a'*40,'123','b'*64,'c'*64)
        self.assertEqual(r['status'],'PASS')
        self.assertFalse(r['production_data_immutability_qualified'])
        self.assertFalse(r['live_nexus_qualified'])
if __name__=='__main__':unittest.main(verbosity=2)
