#!/usr/bin/env python3
"""M25-03 R2A source-only regression. Independent of Gradle and device state."""
from pathlib import Path
import json, re
ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / 'app/src/main/java/com/sdvsync/mods/ModBulkTransaction.kt'
TESTS = ROOT / 'app/src/test/java/com/sdvsync/mods/ModBulkTransactionTest.kt'
POLICY = ROOT / 'docs/security/M3_RELEASE_POLICY.json'

def main():
    a = ENGINE.read_text()
    b = TESTS.read_text()
    assert 'private const val JOURNAL_NAME = "m25-bulk-transaction.properties"' in a
    assert 'FileOutputStream(temp)' in a and 'output.fd.sync()' in a
    assert 'fun recover(): Boolean' in a and 'return@synchronized journal.delete()' in a
    assert 'fun review(' in a and 'fun apply(' in a and 'private fun treeHash(' in a
    assert 'sourceHashes' in a and 'rootWitness' in a and 'inventoryFingerprint' in a
    assert 'ProfileFolderMove' in a and 'PlatformStoragePaths.inspect' in a
    assert 'LinkOption.NOFOLLOW_LINKS' in a and 'Files.isSymbolicLink' in a
    assert 'MAX_STEPS = 512' in a and 'MAX_BYTES' in a
    assert 'MANUAL_REVIEW_REQUIRED' in a
    assert 'usedTokens.add(review.identity)' in a
    for bad in ('enableMod(', 'disableMod(', 'Runtime.getRuntime(', 'ProcessBuilder(',
                'rootShell(', 'su -c', 'http://', 'https://', 'pm clear'):
        assert bad not in a, f'forbidden engine capability: {bad}'
    cases = re.findall(r'@Test fun (\w+)\(', b)
    assert len(cases) >= 11 and len(cases) == len(set(cases)), cases
    for key in ('processDeathAfterJournal', 'collisionAfterPartial', 'modifiedMovedFolder',
                'staleMetadata', 'rootSymlink', 'all512', 'zeroAndTooMany'):
        assert any(x.startswith(key) for x in cases), key
    if POLICY.is_file():
        text = POLICY.read_text()
        for field in ('release_enabled', 'publication_enabled', 'automatic_device_install',
                      'device_qualification_complete'):
            assert re.search(r'"'+field+r'"\s*:\s*false', text), field
    print('M25_03_R2A_SOURCE_POLICY_PASS cases=',len(cases))

if __name__ == '__main__':
    main()
