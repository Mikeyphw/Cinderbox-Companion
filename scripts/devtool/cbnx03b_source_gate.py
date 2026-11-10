#!/usr/bin/env python3
"""CB-NX03B source/security contract; fails on stale emulator roster and lost local consent.

Not equivalent to a real browser or device test.
"""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def source(path):
    file = ROOT / path
    assert file.is_file() and not file.is_symlink(), 'CBNX03B_MISSING:' + path
    return file.read_text(encoding='utf8')

mods = 'app/src/main/java/com/sdvsync/mods/'
bridge = source(mods + 'NexusPairingBridge.kt')
inbox = source(mods + 'NexusPairingInbox.kt')
panel = source('app/src/main/java/com/sdvsync/ui/screens/NexusPairingPanel.kt')
tests = source('app/src/androidTest/java/com/sdvsync/mods/CbNx03PairingDeviceTest.kt')
receipt = source('scripts/devtool/cbnx03_instrumentation_receipt.py')
negative = source('scripts/devtool/cbnx03_hf01_negative_tests.py')
runner = source('scripts/devtool/cbnx03_emulator_ci.sh')
workflow = source('.github/workflows/cbnx03-pairing.yml')
for key in ('private var permitHandoffs = false', 'fun setHandoffEnabled(enabled: Boolean)',
            'method == "POST" && path == "/v1/handoff"',
            'if (!permitHandoffs)', 'NexusPairingInbox.admit(context, id, mod, file)',
            '.put("download_started", false)', '.put("archive_staged", false)',
            '.put("installed", false)', 'NexusPairingInbox.list(context)',
            'inbox_available', 'method == "POST" && path == "/v1/revoke"',
            'MessageDigest.isEqual', 'x-cbnx-nonce',
            'bind(InetSocketAddress(InetAddress.getByName("127.0.0.1"), PORT), 4)'):
    assert key in bridge, 'CBNX03B_BRIDGE_CONTRACT:' + key
for key in ('private const val MAX_PENDING = 8', 'private const val MAX_HISTORY = 32',
            'Regex("[1-9][0-9]{0,11}")', 'Regex("[A-Za-z0-9_-]{22,64}")',
            'fun admit(', 'fun resolve(', 'synchronized(lock)', '.commit()',
            'it.status == "PENDING"', 'already_pending', 'identity_conflict',
            'inbox_full', 'already_seen', '"OPENED"', '"DISMISSED"'):
    assert key in inbox, 'CBNX03B_INBOX_CONTRACT:' + key
assert inbox.count('synchronized(lock)') >= 3, 'CBNX03B_SHARED_ATOMIC_LOCK_INCOMPLETE'
for forbidden in ('startDownload(', 'installFromZip(', 'ModDownloadService(',
                  'getDownloadUrl(', 'getSharedPreferences("nexus', '0.0.0.0',
                  'android.permission.QUERY_ALL_PACKAGES'):
    assert forbidden not in bridge + inbox, 'CBNX03B_PRIVILEGED_CAPABILITY:' + forbidden
for forbidden in ('download_url', 'session_cookie', 'nexus_key', 'nxm://'):
    assert forbidden not in inbox, 'CBNX03B_PERSISTENCE_PRIVACY:' + forbidden
assert 'NexusPairingBridge.setHandoffEnabled(it)' in panel
assert 'NexusPairingInbox.resolve(context, item.id, "OPENED")' in panel
assert 'NexusPairingInbox.resolve(context, item.id, "DISMISSED")' in panel
assert 'NexusBrowserHandoff.createUrl(item.modId, item.fileId)' in panel
assert 'cbnx03b.handoff.open-exact' in panel
assert panel.index('NexusBrowserLauncher.open(context, url)') < panel.index('NexusPairingInbox.resolve(context, item.id, "OPENED")')
# Setter is a UI-only function; HTTP may not invoke it. Gate the entire route on current user approval.
assert bridge.index('if (!permitHandoffs)') < bridge.index('NexusPairingInbox.admit(context, id, mod, file)')
assert 'CbNx03PairingDeviceTest' in runner and 'api-level: 36' in workflow
assert 'cbnx03b_source_gate.py' in workflow and 'cbnx03b_negative_tests.py' in workflow
methods = tuple(re.findall(r'@Test\s+fun\s+([A-Za-z0-9_]+)\(', tests))
assert len(methods) == 7 and len(set(methods)) == 7, 'CBNX03B_DEVICE_TEST_COUNT_DRIFT'
for name in methods:
    assert name in receipt and name in negative, 'CBNX03B_METHOD_MISSING:' + name
assert 'method_events != 14' in receipt and "'test_count': 7 if ok else 0" in receipt
assert "'OK (7 tests)'" in receipt and "block.get('numtests') != '7'" in receipt
assert 'numtests: int = len(METHODS)' in negative and "data['event_count'] == 14" in negative
print('CBNX03B_SOURCE_AND_ROSTER_PASS test_count=7 no_install_capabilities=true')
