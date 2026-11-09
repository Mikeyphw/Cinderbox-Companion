#!/usr/bin/env python3
"""Privacy-only receipt. Never copies raw instrumentation or logcat into artifacts."""
import argparse, json, re
from pathlib import Path
p=argparse.ArgumentParser()
for v in ('log','exit-code','source','run','app-sha','installed-sha','test-sha','output'):
    p.add_argument('--'+v, required=True)
a=p.parse_args()
raw=Path(a.log).read_text(encoding='utf8',errors='replace')
passed=('OK (8 tests)' in raw.replace('\r', ''))
passed = passed and 'FAILURES!!!' not in raw and 'INSTRUMENTATION_FAILED' not in raw and a.exit_code=='0'
passed = passed and a.app_sha==a.installed_sha
receipt={'schema_version':1,'qualification':'CBNX02_API36_SYNTHETIC',
         'status':'PASS' if passed else 'FAIL',
         'source_sha':a.source,'run_id':a.run,
         'test_count':8 if passed else 0,
         'apk_sha256':a.app_sha,'test_apk_sha256':a.test_sha,
         'emulator_only':True,'live_nexus_qualified':False,
         'physical_device_qualified':False,'release_qualified':False,
         'secrets_in_receipt':False}
Path(a.output).write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
if not passed:raise SystemExit('CBNX02_HOSTED_INSTRUMENTATION_REFUSED')
