#!/usr/bin/env python3
"""Reject stale HTTP fixtures, duplicate fixed exact identities and weak diagnostics."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[2]
def load(p):
    f=root/p
    assert f.is_file() and not f.is_symlink(), 'CBNX04_HF02_MISSING:'+p
    return f.read_text()
tests=load('app/src/androidTest/java/com/sdvsync/mods/CbNx03PairingDeviceTest.kt')
receipt=load('scripts/devtool/cbnx03_instrumentation_receipt.py')
workflows=[load('.github/workflows/'+name) for name in ('cbnx03-pairing.yml','cbnx04-authority.yml')]
methods=re.findall(r'@Test\s+fun\s+([A-Za-z_0-9]+)\s*\(',tests)
assert len(methods)==len(set(methods))==7
assert 'socket.soTimeout = 8000' in tests
assert 'val lengths = lines.filter' in tests
assert 'length in 0..65536' in tests
assert 'readBytes()' not in tests.replace('The old readBytes()','')
assert 'private fun distinctFixtureFile()' in tests
assert tests.count('distinctFixtureFile()')>=3
for stage in ('HANDOFF_ADMISSION','HANDOFF_RESOLVE','INBOX_ADMISSION','INBOX_DURABILITY',
              'REVOKE_ACCEPTED','REVOKE_OLD_TOKEN_DENIED'):
    assert 'atStage("'+stage+'")' in tests
    assert "'"+stage+"'" in receipt
assert "'safe_pairing_failure_stages':" in receipt
for needed in ('missing_or_duplicate_start','missing_or_duplicate_success',
               'runner_reported_failure','runner_summary_mismatch','runner_process_failure',
               "'test_count': 7 if ok else 0"):
    assert needed in receipt
for w in workflows:
    assert 'cbnx04_hf02_source_gate.py' in w and 'cbnx04_hf02_negative_tests.py' in w
    assert ':app:assembleDebugAndroidTest' in w
print('CBNX04B_PAIRING_SECURITY_AND_CANONICAL_CONTRACT_PASS')

ROOT=root

# CB-NX04B migration: this regression check must track the CURRENT canonical
# archive-provenance authority suite; no obsolete seven-method authority contract.
authority_receipt = (ROOT/'scripts/devtool/cbnx04_instrumentation_receipt.py').read_text()
authority_source = (ROOT/'app/src/main/java/com/sdvsync/mods/NexusPairingAuthority.kt').read_text()
archive_source = (ROOT/'app/src/main/java/com/sdvsync/mods/NexusArchiveProvenance.kt').read_text()
assert 'CBNX04D_API36_SYNTHETIC_NATIVE_UPDATES_EVIDENCE' in authority_receipt
assert 'method_events != 36' in authority_receipt
assert "'test_count': 18 if ok else 0" in authority_receipt
assert '.put("archive_checksum_qualified", verified)' in authority_source
assert 'NexusArchiveProvenance.inspect(records, privateReviewRoot)' in authority_source
assert 'MessageDigest.getInstance("SHA-256")' in archive_source
assert 'record.modId != mod || record.fileId != file' in archive_source
assert 'method_events != 14' not in authority_receipt
print('CBNX04C_MIGRATED_HF02_SOURCE_GATE_CANONICAL_PASS')

assert "SMAPI_CACHE_FRESH" in (ROOT/"app/src/main/java/com/sdvsync/mods/NexusUpdateEvidence.kt").read_text()
