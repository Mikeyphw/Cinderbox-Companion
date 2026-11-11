#!/usr/bin/env python3
"""Fail-closed source and signature mutation negatives: never touches device data."""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from cbnx06_full_lab_gate import ROOT, Refused, check
from cbnx06_full_lab_artifact import Refused as ArtifactRefused, verify_signer

EXPECTED_FILES = [
    'app/build.gradle.kts',
    'app/src/cbnxLab/AndroidManifest.xml',
    'app/src/main/java/com/sdvsync/cinderbox/CinderboxPaths.kt',
    'app/src/main/java/com/sdvsync/cinderbox/CinderboxLabBoundary.kt',
    'app/src/main/java/com/sdvsync/SdvSyncApp.kt',
    'app/src/main/java/com/sdvsync/MainActivity.kt',
    'app/src/main/java/com/sdvsync/local/StoragePreflight.kt',
    'app/src/main/java/com/sdvsync/fileaccess/FileAccessDetector.kt',
    'app/src/main/java/com/sdvsync/di/AppModule.kt',
    'app/src/main/java/com/sdvsync/saves/SaveFileManager.kt',
    'app/src/main/java/com/sdvsync/download/GameDownloadManager.kt',
    'app/src/main/java/com/sdvsync/mods/ModFileManager.kt',
    'app/src/main/java/com/sdvsync/mods/NexusPairingBridge.kt',
    'app/src/main/java/com/sdvsync/ui/screens/NexusPairingPanel.kt',
    'scripts/devtool/cbnx06_full_lab_gate.py',
    '.github/workflows/cbnx06-full-cinderbox-lab.yml',
]

class NegativeSources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):check(ROOT)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cbnx-full-lab-negative-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for rel in EXPECTED_FILES:
            dest=self.root/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/rel,dest)

    def refuses(self,path,from_text,to_text,reason):
        file=self.root/path
        text=file.read_text()
        self.assertIn(from_text,text)
        file.write_text(text.replace(from_text,to_text,1))
        with self.assertRaisesRegex(Refused,reason):check(self.root)

    def test_wrong_lab_package_suffix(self):self.refuses('app/build.gradle.kts','.cbnx06lab','.prod', 'LAB_GRADLE_BUILD_VARIANT_INCOMPLETE')
    def test_lab_build_config_removed(self):self.refuses('app/build.gradle.kts','"CBNX_LAB", "true"','"CBNX_LAB", "false"','LAB_GRADLE_BUILD_VARIANT_INCOMPLETE')
    def test_missing_manifest_storage_deny(self):self.refuses('app/src/cbnxLab/AndroidManifest.xml','android.permission.MANAGE_EXTERNAL_STORAGE','android.permission.ACCESS_NETWORK_STATE','LAB_PRIVILEGED_PERMISSION_NOT_REMOVED')
    def test_nxm_interception(self):self.refuses('app/src/cbnxLab/AndroidManifest.xml','android.intent.action.MAIN','android.intent.action.VIEW','LAB_NXM_VIEW_INTERCEPTION')
    def test_more_than_one_filter(self):self.refuses('app/src/cbnxLab/AndroidManifest.xml','</intent-filter>','</intent-filter><intent-filter/>','LAB_UNEXPECTED_INTENT_FILTERS')
    def test_disable_activity_manifest_override(self):self.refuses('app/src/cbnxLab/AndroidManifest.xml','tools:node="replace"','tools:node="merge"','LAB_ACTIVITY_NOT_REPLACED')
    def test_missing_shizuku_removal(self):self.refuses('app/src/cbnxLab/AndroidManifest.xml','rikka.shizuku.ShizukuProvider','other.Provider','LAB_PRODUCTION_COMPONENT_NOT_REMOVED')
    def test_wrong_root_package(self):self.refuses('app/src/main/java/com/sdvsync/cinderbox/CinderboxLabBoundary.kt','com.sdvsync.cbnx06lab','com.sdvsync','LAB_STORAGE_GUARD_MISSING')
    def test_missing_symlink_deny(self):self.refuses('app/src/main/java/com/sdvsync/cinderbox/CinderboxLabBoundary.kt','LAB_SYMLINK_REFUSED','LAB_UNCHECKED_LINK','LAB_STORAGE_GUARD_MISSING')
    def test_missing_storage_preflight(self):self.refuses('app/src/main/java/com/sdvsync/local/StoragePreflight.kt','CinderboxLabBoundary.isPrivate(destination)','true','LAB_GUARD_MISSING')
    def test_missing_private_mod_root(self):self.refuses('app/src/main/java/com/sdvsync/mods/ModFileManager.kt','CinderboxLabBoundary.requireModsRoot(modsDir)','//unchecked','LAB_GUARD_MISSING')
    def test_bypass_save_redirection(self):self.refuses('app/src/main/java/com/sdvsync/saves/SaveFileManager.kt','if (BuildConfig.CBNX_LAB) CinderboxPaths.SAVES_DIR else','if (false) CinderboxPaths.SAVES_DIR else','LAB_GUARD_MISSING')
    def test_pairing_production_port_reuse(self):self.refuses('app/src/main/java/com/sdvsync/mods/NexusPairingBridge.kt','if (BuildConfig.CBNX_LAB) 38472 else PORT','if (BuildConfig.CBNX_LAB) PORT else PORT','LAB_GUARD_MISSING')
    def test_comment_only_real_root_is_not_runtime_path(self):
        p = self.root/'app/src/main/java/com/sdvsync/mods/Documentation.kt'
        p.write_text('// Production documentation: /storage/emulated/0/StardewValley\n/* Nested docs /* note */ /storage/emulated/0/StardewValley */\nval uri = "http://127.0.0.1/ok"\n')
        check(self.root)

    def test_raw_string_unclassified_real_root_refused(self):
        p = self.root/'app/src/main/java/com/sdvsync/mods/HiddenLiteral.kt'
        p.write_text('val p = """/storage/emulated/0/StardewValley"""\n')
        with self.assertRaisesRegex(Refused,'LAB_UNCLASSIFIED_PRODUCTION_ROOT'):
            check(self.root)

    def test_unclassified_real_root(self):
        p=self.root/'app/src/main/java/com/sdvsync/mods/UnreviewedWrite.kt';p.write_text('val p="/storage/emulated/0/StardewValley"')
        with self.assertRaisesRegex(Refused,'LAB_UNCLASSIFIED_PRODUCTION_ROOT'):check(self.root)
    def test_reintroduced_compiletime_root(self):
        p=self.root/'app/src/main/java/com/sdvsync/mods/UnreviewedConstant.kt';p.write_text('const val ROOT = CinderboxPaths.MODS_DIR')
        with self.assertRaisesRegex(Refused,'LAB_COMPILETIME_PATH_REMAINS'):check(self.root)
    def test_lost_hosted_gradle(self):self.refuses('.github/workflows/cbnx06-full-cinderbox-lab.yml',':app:assembleCbnxLab',':app:assembleDebug','LAB_CI_GUARD_MISSING')

class SignerNegatives(unittest.TestCase):
    CERT='ab'*32
    def output(self):return 'Verified using v2 scheme (APK Signature Scheme v2): true\nV2 Signer: certificate SHA-256 digest: '+self.CERT+'\n'
    def test_one_v2_signer(self):self.assertEqual(verify_signer(self.output()),self.CERT)
    def test_missing_v2(self):
        with self.assertRaisesRegex(ArtifactRefused,'APK_V2_REQUIRED'):verify_signer('V2 Signer: certificate SHA-256 digest: '+self.CERT)
    def test_malformed_signer(self):
        with self.assertRaisesRegex(ArtifactRefused,'APK_SIGNER_LABEL_UNRECOGNIZED'):verify_signer(self.output()+'Mystery Signer: certificate SHA-256 digest: '+self.CERT+'\n')
    def test_different_v3_signer(self):
        with self.assertRaisesRegex(ArtifactRefused,'APK_SIGNERS_NOT_ONE_CERTIFICATE'):verify_signer(self.output()+'V3.0 Signer: certificate SHA-256 digest: '+'cd'*32+'\n')
    def test_duplicate_legacy_signers(self):
        o='Verified using v2 scheme (APK Signature Scheme v2): true\n'
        with self.assertRaisesRegex(ArtifactRefused,'APK_LEGACY_SIGNER_COUNT_NOT_ONE'):verify_signer(o+'Signer #1 certificate SHA-256 digest: '+self.CERT+'\nSigner #2 certificate SHA-256 digest: '+self.CERT+'\n')
    def test_duplicate_v2_signers_refused(self):
        with self.assertRaisesRegex(ArtifactRefused,'APK_SCHEME_SIGNER_COUNT_NOT_ONE'):
            verify_signer(self.output()+'V2 Signer: certificate SHA-256 digest: '+self.CERT+'\n')

if __name__=='__main__':unittest.main(verbosity=2)
