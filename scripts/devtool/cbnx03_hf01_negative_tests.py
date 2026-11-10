#!/usr/bin/env python3
"""HF01 offline Android instrumentation parser and read-only-bridge negatives.

This is deliberately a source/receipt gate, not synthetic device qualification.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PARSER = ROOT / 'scripts/devtool/cbnx03_instrumentation_receipt.py'
BRIDGE = ROOT / 'app/src/main/java/com/sdvsync/mods/NexusPairingBridge.kt'
TESTS = ROOT / 'app/src/androidTest/java/com/sdvsync/mods/CbNx03PairingDeviceTest.kt'
METHODS = (
    'optInRequiredAndLoopbackOnly',
    'pairingReadOnlyAndNonceReplayFails',
    'revokeInvalidatesTokenAndStopsListening',
    'incorrectCodesLockOutPairing',
)
CLASS = 'com.sdvsync.mods.CbNx03PairingDeviceTest'


def event(name: str, status: int, klass: str = CLASS, numtests: int = 4) -> str:
    return ''.join((
        f'INSTRUMENTATION_STATUS: class={klass}\n',
        'INSTRUMENTATION_STATUS: id=AndroidJUnitRunner\n',
        f'INSTRUMENTATION_STATUS: numtests={numtests}\n',
        f'INSTRUMENTATION_STATUS: test={name}\n',
        f'INSTRUMENTATION_STATUS_CODE: {status}\n',
    ))


def valid_log() -> str:
    return ''.join(event(n, 1) + event(n, 0) for n in METHODS) + (
        'INSTRUMENTATION_RESULT: stream=\nTime: 0.3\n\nOK (4 tests)\n'
        'INSTRUMENTATION_CODE: -1\n'
    )


with TemporaryDirectory(prefix='cbnx03-hf01-gate-') as tmp:
    log = Path(tmp) / 'private-raw.txt'
    receipt = Path(tmp) / 'STATUS.json'

    def execute(raw: str, rc: str = '0'):
        log.write_text(raw, encoding='utf8')
        result = subprocess.run([
            sys.executable, '-B', str(PARSER), '--log', str(log), '--exit', rc,
            '--source', 'a' * 40, '--run', '123', '--app-sha', 'b' * 64,
            '--test-sha', 'c' * 64, '--output', str(receipt),
        ], capture_output=True, text=True, timeout=15)
        payload = json.loads(receipt.read_text(encoding='utf8'))
        return result, payload

    good = valid_log()
    process, data = execute(good)
    assert process.returncode == 0 and data['status'] == 'PASS', 'CBNX03_HF01_VALID_ANDROID_EVENT_STREAM_REJECTED'
    assert data['test_count'] == 4 and data['event_count'] == 8
    assert data['test_results'] == {name: 'PASS' for name in METHODS}
    assert data['failure_reason_codes'] == []

    negative = [
        ('duplicate completion', good.replace(event(METHODS[0], 0), event(METHODS[0], 0) * 2), '0'),
        ('duplicate start', good.replace(event(METHODS[1], 1), event(METHODS[1], 1) * 2), '0'),
        ('failed junit assertion', good.replace(event(METHODS[2], 0), event(METHODS[2], -2)), '0'),
        ('missing success', good.replace(event(METHODS[1], 0), ''), '0'),
        ('method name drift', good.replace(event(METHODS[3], 0), event('OtherMethod', 0)), '0'),
        ('class drift', good.replace(event(METHODS[0], 0), event(METHODS[0], 0, klass='org.evil.Attack')), '0'),
        ('numtests drift', good.replace(event(METHODS[0], 0), event(METHODS[0], 0, numtests=8)), '0'),
        ('failure banner', good + 'FAILURES!!!\n', '0'),
        ('missing success banner', good.replace('OK (4 tests)', 'OK (3 tests)'), '0'),
        ('missing final runner code', good.replace('INSTRUMENTATION_CODE: -1', 'INSTRUMENTATION_CODE: 0'), '0'),
        ('shell exit failure', good, '1'),
        ('single status per method stale fixture', ''.join(f'INSTRUMENTATION_STATUS: test={n}\n' for n in METHODS) + 'INSTRUMENTATION_CODE: -1\nOK (4 tests)\n', '0'),
    ]
    for title, raw, rc in negative:
        process, payload = execute(raw, rc)
        assert process.returncode != 0 and payload['status'] == 'FAIL', 'CBNX03_HF01_NEGATIVE_ESCAPED:' + title
        assert payload['test_count'] == 0, 'CBNX03_HF01_PARTIAL_TESTS_MARKED_PASS:' + title
        assert payload['failure_reason_codes'], 'CBNX03_HF01_MISSING_SAFE_DIAGNOSTIC:' + title
    secret = 'nexus-key-example-private-canary-739'
    process, data = execute(good.replace('OK (4 tests)', 'OK (4 tests)\nINSTRUMENTATION_RESULT: stream=' + secret))
    assert process.returncode == 0 and secret not in str(data) and secret not in process.stdout

    bridge = BRIDGE.read_text(encoding='utf8')
    tests = TESTS.read_text(encoding='utf8')
    assert 'bind(InetSocketAddress(InetAddress.getByName("127.0.0.1"), PORT), 4)' in bridge
    assert 'reuseAddress = true' in bridge
    assert 'if (headers.containsKey(key))' in bridge
    assert 'respond(output, 403, JSONObject().put("error", "refused"), null)' in bridge
    assert '"hOsT" to "evil.example"' in tests
    for restricted in ('startDownload(', 'installFromZip(', '0.0.0.0', 'android.permission.QUERY_ALL_PACKAGES'):
        assert restricted not in bridge, 'CBNX03_HF01_FORBIDDEN_BRIDGE_CAPABILITY:' + restricted

print('CBNX03_HF01_ANDROID_RECEIPT_AND_SECURITY_NEGATIVES_PASS negative_cases=12 privacy_canary=1')
