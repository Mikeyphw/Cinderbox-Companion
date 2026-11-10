#!/usr/bin/env python3
"""CB-NX04 HF03: bind retry is bounded, all historical contracts retained."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]
def src(p):
    file=ROOT/p
    assert file.is_file() and not file.is_symlink(), 'CBNX04_HF03_MISSING:'+p
    return file.read_text(encoding='utf-8')
mods='app/src/main/java/com/sdvsync/mods/'
bridge=src(mods+'NexusPairingBridge.kt')
binder=src(mods+'NexusLoopbackBindPolicy.kt')
device=src('app/src/androidTest/java/com/sdvsync/mods/CbNx03PairingDeviceTest.kt')
unit=src('app/src/test/java/com/sdvsync/mods/NexusLoopbackBindPolicyTest.kt')
receipt=src('scripts/devtool/cbnx03_instrumentation_receipt.py')
assert 'NexusLoopbackBindPolicy.acquire(bind = {' in bridge, 'CBNX04_HF03_MISSING_NAMED_BIND_ARGUMENT'
assert 'NexusLoopbackBindPolicy.acquire {' not in bridge, 'CBNX04_HF03_STALE_TRAILING_LAMBDA'
assert 'fun <T> acquire(bind: () -> T, pause:' in binder, 'CBNX04_HF03_BIND_SIGNATURE_MOVED'
assert '        })\n        listener = socket' in bridge, 'CBNX04_HF03_BIND_LAMBDA_NOT_CLOSED'
assert 'candidate.reuseAddress = true' in bridge
assert 'candidate.bind(InetSocketAddress(InetAddress.getByName("127.0.0.1"), PORT), 4)' in bridge
assert 'candidate.close()' in bridge
assert 'MAX_ATTEMPTS = 5' in binder and 'BACKOFF_MS = 90L' in binder
assert 'catch (error: BindException)' in binder
assert 'if (attempt == MAX_ATTEMPTS) throw error' in binder
assert 'pause(BACKOFF_MS)' in binder
assert 'catch (error: Exception)' not in binder and '0.0.0.0' not in binder
assert 'repeat(4)' in device and 'assertEquals(200, request("GET", "/v1/hello").first)' in device
assert 'CBNX03_SAFE_CAUSE_' in device
assert 'safe_pairing_failure_causes' in receipt and 'safe_pairing_failure_cause' in receipt
assert "'BIND_IN_USE'" in receipt and "'SOCKET_FAILURE'" in receipt
methods=re.findall(r'@Test\s+fun\s+([A-Za-z0-9_]+)\s*\(',device)
assert len(set(methods))==len(methods)==7, methods
unit_methods=re.findall(r'@Test\s+fun\s+([A-Za-z0-9_]+)\s*\(',unit)
assert len(set(unit_methods))==len(unit_methods)==4, unit_methods
for workflow in ('cbnx03-pairing.yml','cbnx04-authority.yml'):
    w=src('.github/workflows/'+workflow)
    assert 'cbnx04_hf02_source_gate.py' in w and 'cbnx04_hf02_negative_tests.py' in w
    for marker in ('cbnx04_hf03_source_gate.py','cbnx04_hf03_negative_tests.py',
                   ':app:testDebugUnitTest', ':app:assembleDebugAndroidTest'):
        assert marker in w, workflow +':'+marker
print('CBNX04_HF03_FIX02_NAMED_BIND_AND_STALE_CONTRACT_PASS methods=7 unit=4')
