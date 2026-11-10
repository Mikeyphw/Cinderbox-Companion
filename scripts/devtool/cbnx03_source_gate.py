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
for word in ('bind(InetSocketAddress(InetAddress.getByName("127.0.0.1"), PORT), 4)',
             'reuseAddress = true',
             'if (headers.containsKey(key))',
             'respond(output, 403, JSONObject().put("error", "refused"), null)',
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
assert 'cbnx03_hf01_negative_tests.py' in workflow, 'CBNX03_HF01_HOSTED_NEGATIVE_TESTS_NOT_WIRED'
receipt = read('scripts/devtool/cbnx03_instrumentation_receipt.py')
for contract in ("elif code == '0'", "elif code == '1'", "'test_results': results", "'failure_reason_codes': reason_codes"):
    assert contract in receipt, 'CBNX03_HF01_RECEIPT_CONTRACT_STALE:' + contract
runner = read('scripts/devtool/cbnx03_emulator_ci.sh')
assert 'cbnx03_instrumentation_receipt.py' in runner, 'CBNX03_HF01_RUNNER_RECEIPT_MISSING'
assert 'hOsT' in tests, 'CBNX03_HF01_MISSING_DUPLICATE_HOST_CASE'

policy = json.loads(read('docs/security/M3_RELEASE_POLICY.json'))
for flag in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
    assert policy[flag] is False, 'CBNX03_RELEASE_FLAG_CHANGED:'+flag
print('CBNX03A_ANDROID_SOURCE_PASS_RUNTIME_UNQUALIFIED')
