#!/usr/bin/env python3
"""CB-NX03A security and historical-contract gates; static only, not device proof."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def read(path):
    p = ROOT/path
    assert p.is_file() and not p.is_symlink(), 'CBNX03_FILE_MISSING:'+path
    return p.read_text(encoding='utf-8')
bridge = read('app/src/main/java/com/sdvsync/mods/NexusPairingBridge.kt')
settings = read('app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt')
panel = read('app/src/main/java/com/sdvsync/ui/screens/NexusPairingPanel.kt')
tests = read('app/src/androidTest/java/com/sdvsync/mods/CbNx03PairingDeviceTest.kt')
workflow = read('.github/workflows/cbnx03-pairing.yml')
for word in ('ServerSocket(PORT, 4, InetAddress.getByName("127.0.0.1"))',
             'val allowedOrigin', 'x-cbnx-nonce', 'MessageDigest.isEqual',
             'proof_kind", "journal_only"', 'installed_inventory_qualified',
             'private const val WINDOW_MS = 10 * 60_000L', 'stopLocked()',
             'challenges.remove(challengeSent)', 'guesses >= 5'):
    assert word in bridge, 'CBNX03_SECURITY_CONTRACT_MISSING:'+word
for forbidden in ('installFromZip(', 'startDownload(', 'su -c', 'android.permission.QUERY_ALL_PACKAGES', '0.0.0.0'):
    assert forbidden not in bridge, 'CBNX03_FORBIDDEN_BRIDGE_CAPABILITY:'+forbidden
assert 'NexusPairingPanel()' in settings
assert 'NexusPairingBridge.start(context)' in panel
for test in ('optInRequiredAndLoopbackOnly', 'pairingReadOnlyAndNonceReplayFails',
             'revokeInvalidatesTokenAndStopsListening', 'incorrectCodesLockOutPairing'):
    assert test in tests, 'CBNX03_MISSING_EMULATOR_TEST:'+test
assert 'CbNx03PairingDeviceTest' in workflow and 'api-level: 36' in workflow
policy = json.loads(read('docs/security/M3_RELEASE_POLICY.json'))
for flag in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
    assert policy[flag] is False, 'CBNX03_RELEASE_FLAG_CHANGED:'+flag
print('CBNX03A_ANDROID_SOURCE_PASS_RUNTIME_UNQUALIFIED')
