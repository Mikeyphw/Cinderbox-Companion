#!/usr/bin/env python3
"""CB-NX03 HF01: exact AndroidJUnitRunner event receipt, never raw logs or secrets.

AndroidJUnitRunner emits *two* status blocks per method (start=1, pass=0).
Any failing/unknown event, missing end marker or stale method roster fails closed.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

p = argparse.ArgumentParser()
for arg in ('log', 'exit', 'source', 'run', 'app-sha', 'test-sha', 'output'):
    p.add_argument('--' + arg, required=True)
a = p.parse_args()
raw = Path(a.log).read_text(encoding='utf-8', errors='replace').replace('\r', '')
methods = (
    'optInRequiredAndLoopbackOnly',
    'pairingReadOnlyAndNonceReplayFails',
    'revokeInvalidatesTokenAndStopsListening',
    'incorrectCodesLockOutPairing',
    'exactFileHandoffRequiresLocalOptInAndNeverStartsDownload',
    'invalidIdentityReplayAndConcurrentDuplicateAreFailClosed',
    'inboxSurvivesBridgeShutdownWithoutReenqueuingAnything',
)
allowed = set(methods)
expected_class = 'com.sdvsync.mods.CbNx03PairingDeviceTest'
# Allowlisted diagnostic labels only; stack details never enter redacted receipts.
SAFE_STAGES = set((
    'START', 'PAIR', 'STATE_FETCH', 'STATE_ASSERT', 'NONCE_REPLAY', 'NO_INSTALL_ENDPOINT',
    'HANDOFF_START', 'HANDOFF_PAIR', 'HANDOFF_OPT_IN_GUARD', 'HANDOFF_LOCAL_ENABLE',
    'HANDOFF_ADMISSION', 'HANDOFF_STATE', 'HANDOFF_RESOLVE',
    'INBOX_START', 'INBOX_PAIR', 'INBOX_OPT_IN', 'INBOX_ADMISSION', 'INBOX_STOP',
    'INBOX_DURABILITY', 'INBOX_NO_DOWNLOAD',
    'REVOKE_START', 'REVOKE_PAIR', 'REVOKE_ACCEPTED',
    'REVOKE_OLD_TOKEN_DENIED', 'REVOKE_STOP'
))
safe_stages = {}
start = Counter()
passed = Counter()
failed = Counter()
unknown_count = 0
method_events = 0
block = {}

for line in raw.splitlines():
    if line.startswith('INSTRUMENTATION_STATUS: '):
        kv = line[len('INSTRUMENTATION_STATUS: '):]
        key, sep, value = kv.partition('=')
        if sep and key in ('test', 'class', 'numtests'):
            block[key] = value.strip()
        elif sep and key == 'stack':
            # Extract only the fixed label, never exception detail or secret-bearing URL.
            match = re.search(r'CBNX03_SAFE_STAGE_([A-Z_]+)', value)
            if match and match.group(1) in SAFE_STAGES:
                block['safe_stage'] = match.group(1)
    elif line.startswith('INSTRUMENTATION_STATUS_CODE: '):
        code = line.split(': ', 1)[1].strip()
        method = block.get('test')
        klass = block.get('class')
        if method:
            method_events += 1
            if method not in allowed or klass != expected_class or block.get('numtests') != '7':
                unknown_count += 1
            elif code == '1':
                start[method] += 1
            elif code == '0':
                passed[method] += 1
            else:
                failed[method] += 1
                if block.get('safe_stage') in SAFE_STAGES:
                    safe_stages[method] = block['safe_stage']
        block = {}

reason_codes = []
def fail(code, condition):
    if condition:
        reason_codes.append(code)

fail('unexpected_method_or_class', unknown_count != 0)
fail('invalid_runner_event_count', method_events != 14)
fail('missing_or_duplicate_start', any(start[n] != 1 for n in methods))
fail('missing_or_duplicate_success', any(passed[n] != 1 for n in methods))
fail('runner_reported_failure', any(failed[n] for n in methods) or
     'FAILURES!!!' in raw or 'INSTRUMENTATION_FAILED' in raw)
fail('runner_summary_mismatch', 'OK (7 tests)' not in raw or
     'INSTRUMENTATION_CODE: -1' not in raw)
fail('runner_process_failure', a.exit != '0')
fail('source_or_apk_hash_invalid', not re.fullmatch(r'[0-9a-f]{40}', a.source) or
     not all(re.fullmatch(r'[0-9a-f]{64}', h) for h in (a.app_sha, a.test_sha)))

ok = not reason_codes
results = {name: ('PASS' if start[name] == 1 and passed[name] == 1 and not failed[name]
                  else 'FAIL' if failed[name] else 'INCOMPLETE') for name in methods}
receipt = {
    'schema_version': 2,
    'qualification': 'CBNX03_API36_SYNTHETIC_READ_ONLY',
    'status': 'PASS' if ok else 'FAIL',
    'source_sha': a.source, 'run_id': a.run,
    'test_count': 7 if ok else 0,
    'test_methods': list(methods) if ok else [],
    'test_results': results,
    'event_count': method_events,
    'unexpected_event_count': unknown_count,
    'failure_reason_codes': reason_codes,
    # Fixed enumeration from the one failing test only. No raw exception/response/secret.
    'safe_pairing_failure_stages': {name: safe_stages[name] for name in methods
                                     if failed[name] and name in safe_stages},
    'safe_pairing_failure_stage': next((safe_stages[name] for name in methods
                                        if failed[name] and name in safe_stages), None),
    'app_sha256': a.app_sha, 'test_apk_sha256': a.test_sha,
    'emulator_only': True, 'live_firefox_qualified': False,
    'physical_device_qualified': False, 'live_nexus_qualified': False,
    'release_qualified': False, 'secrets_in_receipt': False,
}
Path(a.output).write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
# Only allowlisted names and fixed reason codes are printed. Never echo raw log.
print('CBNX03_HF01_RECEIPT_STATUS=' + receipt['status'])
if not ok:
    print('CBNX03_HF01_SAFE_FAILURE_CODES=' + ','.join(reason_codes))
    raise SystemExit('CBNX03_HOSTED_INSTRUMENTATION_REFUSED')
print('CBNX03B_API36_EXACT_SEVEN_TESTS_PASS')
