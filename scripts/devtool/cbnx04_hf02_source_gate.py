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
print('CBNX04_HF02_SEVEN_METHOD_STALE_CONTRACT_PASS')
