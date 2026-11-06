#!/usr/bin/env python3
"""Non-Gradle source safety gate for M25-03 R2B's witnessed read-only UI."""
from pathlib import Path
import json, re
ROOT = Path(__file__).resolve().parents[2]
FILE_MANAGER = ROOT/'app/src/main/java/com/sdvsync/mods/ModFileManager.kt'
SELECTION = ROOT/'app/src/main/java/com/sdvsync/mods/ModSelectionPolicy.kt'
VM = ROOT/'app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt'
SCREEN = ROOT/'app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt'
ENGINE = ROOT/'app/src/main/java/com/sdvsync/mods/ModBulkTransaction.kt'
TESTS = ROOT/'app/src/androidTest/java/com/sdvsync/mods/ModBulkReadOnlyDeviceTest.kt'
POLICY = ROOT/'docs/security/M3_RELEASE_POLICY.json'


def main():
    fm, sel, vm, screen, eng, tests = (p.read_text() for p in
        (FILE_MANAGER, SELECTION, VM, SCREEN, ENGINE, TESTS))
    assert 'fun previewBulkWithWitness(' in fm
    assert 'bulkTransactions.review(' in fm
    assert 'Avoid parseMod()' in fm and 'manifestFile.length() in 1..262144L' in fm
    assert 'physical.sourceHashes[index]' in fm and 'physical.rootWitness' in fm
    assert 'MessageDigest.getInstance("SHA-256")' in fm
    assert 'return preview.copy(filesystemWitness = proof)' in fm
    assert 'bulkTransactions.recover()' in fm
    assert fm.count('check(bulkTransactions.recover())') >= 7
    assert 'fun applyBulk' not in fm and 'bulkTransactions.apply(' not in fm
    assert 'filesystemWitness: String? = null' in sel
    assert 'fileManager.previewBulkWithWitness(selected, enable)' in vm
    assert 'isPreparingBulkPreview' in vm and 'Dispatchers.IO' in vm
    assert 'Bulk preview unavailable; no mod folders were changed' in vm
    assert 'preview.filesystemWitness' in screen and 'Live bulk apply is not enabled' in screen
    assert 'viewModel.confirmBulk' not in screen and 'viewModel.applyBulk' not in screen
    assert 'fun apply(' in eng and 'internal class ModBulkTransaction' in eng
    cases = re.findall(r'@Test fun (\w+)\(',tests)
    assert len(cases) == 4 and len(set(cases)) == 4, cases
    assert 'Files.createTempDirectory(context.cacheDir.toPath()' in tests
    assert 'CinderboxPaths.MODS_DIR' not in tests
    safety = json.loads(POLICY.read_text())
    for key in ('release_enabled','publication_enabled','automatic_device_install',
                'device_qualification_complete'):
        assert safety[key] is False, key
    print('M25_03_R2B_READONLY_SOURCE_PASS tests=',len(cases))

if __name__ == '__main__':
    main()
