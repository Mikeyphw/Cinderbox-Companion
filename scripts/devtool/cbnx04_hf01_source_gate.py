#!/usr/bin/env python3
"""CB-NX04A HF01: nonblocking authority, complete original pairing roster and privacy."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]
def src(path):
    f=ROOT/path
    assert f.is_file() and not f.is_symlink(), 'CBNX04_HF01_MISSING:'+path
    return f.read_text(encoding='utf8')
mods='app/src/main/java/com/sdvsync/mods/'
bridge=src(mods+'NexusPairingBridge.kt')
cache=src(mods+'NexusPairingAuthorityCache.kt')
tests=src('app/src/androidTest/java/com/sdvsync/mods/CbNx03PairingDeviceTest.kt')
unit=src('app/src/test/java/com/sdvsync/mods/NexusPairingAuthorityCacheTest.kt')
receipt=src('scripts/devtool/cbnx03_instrumentation_receipt.py')
workflow=src('.github/workflows/cbnx03-pairing.yml')
authority_workflow=src('.github/workflows/cbnx04-authority.yml')
assert 'private val authorityCache = NexusPairingAuthorityCache' in bridge
assert bridge.count('authorityCache.invalidate()') == 2
assert 'authorityCache.getOrLaunch(' in bridge
assert bridge.count('NexusPairingAuthority.snapshot(')==1
assert 'ModDownloadJournal.revision.value' in bridge
assert '"installed_inventory_qualified", false' in bridge
assert '"proof_kind", "journal_only"' in bridge
assert '"inventory_state", "REFRESHING"' in bridge
assert 'class NexusPairingAuthorityCache(' in cache
for marker in ('private var inFlight = false','if (!inFlight)', 'requestGeneration == generation',
    'generation++','data = null','isDaemon = true','Thread({', 'getOrLaunch(', 'fun invalidate()'):
    assert marker in cache, 'CBNX04_HF01_CACHE_CONTRACT_MISSING:'+marker
assert not any(x in cache for x in ('installFromZip(', 'startDownload(', 'renameTo(', 'deleteRecursively(', 'SharedPreferences('))
assert 'CBNX03_SAFE_STAGE_$stage' in tests
assert 'safe_pairing_failure_stage' in receipt
methods=tuple(re.findall(r'@Test\s+fun\s+([A-Za-z_0-9]+)\s*\(',tests))
assert len(methods)==7 and len(set(methods))==7
assert 'pairingReadOnlyAndNonceReplayFails' in methods
unitmethods=tuple(re.findall(r'@Test\s+fun\s+([A-Za-z_0-9]+)\s*\(',unit))
assert len(unitmethods)==4 and len(set(unitmethods))==4
for gate in ('cbnx04_hf01_source_gate.py','cbnx04_hf01_negative_tests.py'):
    assert gate in workflow and gate in authority_workflow
assert ':app:testDebugUnitTest' in workflow and ':app:testDebugUnitTest' in authority_workflow
print('CBNX04_HF01_NONBLOCKING_SOURCE_AND_STALE_CONTRACT_PASS pairing=7 cache=4')
