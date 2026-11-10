#!/usr/bin/env python3
"""Fail-closed API36 receipt. Raw logs are never uploaded."""
import argparse
import json
import re
from pathlib import Path
p=argparse.ArgumentParser()
for key in ('log','exit','source','run','app-sha','test-sha','output'):
    p.add_argument('--'+key,required=True)
a=p.parse_args()
s=Path(a.log).read_text(encoding='utf-8', errors='replace').replace('\r','')
tests=('optInRequiredAndLoopbackOnly', 'pairingReadOnlyAndNonceReplayFails',
       'revokeInvalidatesTokenAndStopsListening', 'incorrectCodesLockOutPairing')
observed=re.findall(r'INSTRUMENTATION_STATUS: test=([^\n]+)',s)
pass_count=len(observed)==len(tests) and set(observed)==set(tests)
pass_count &= 'OK (4 tests)' in s and 'FAILURES!!!' not in s
pass_count &= 'INSTRUMENTATION_FAILED' not in s and 'INSTRUMENTATION_CODE: -1' in s
pass_count &= a.exit=='0' and bool(re.fullmatch('[0-9a-f]{40}',a.source))
pass_count &= all(re.fullmatch('[0-9a-f]{64}',h) for h in (a.app_sha,a.test_sha))
receipt={'schema_version':1,'qualification':'CBNX03_API36_SYNTHETIC_READ_ONLY',
         'status':'PASS' if pass_count else 'FAIL', 'source_sha':a.source,
         'run_id':a.run,'test_count':4 if pass_count else 0,
         'test_methods':list(tests) if pass_count else [],
         'app_sha256':a.app_sha,'test_apk_sha256':a.test_sha,
         'emulator_only':True,'live_firefox_qualified':False,
         'physical_device_qualified':False,'live_nexus_qualified':False,
         'release_qualified':False,'secrets_in_receipt':False}
Path(a.output).write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
if not pass_count: raise SystemExit('CBNX03_HOSTED_INSTRUMENTATION_REFUSED')
