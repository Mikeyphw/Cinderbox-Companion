#!/usr/bin/env python3
"""UI-D02 source-bound JSON evidence, reusable in Devtool and GitHub Actions."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from ui_d02_source import verify, ROOT

REQUIRED = (
    '.devtool.toml',
    'app/src/androidTest/java/com/sdvsync/qualification/EarthyComponentsDeviceTest.kt',
    'scripts/devtool/ui_d02_source.py',
    'scripts/devtool/ui_d02_gate.py',
    'scripts/devtool/test_ui_d02.py',
    'docs/security/M3_RELEASE_POLICY.json',
)


def produce():
    source = verify()
    inv = dict(source['source_sha256'])
    for rel in REQUIRED:
        f = ROOT/rel
        if not f.is_file() or f.is_symlink():
            return {'schema_version':1, 'producer':'cinderbox-ui-d02-devtool','overall':'BLOCKED_SOURCE_MISSING','missing_path':rel,'release_qualified':False,'publication_allowed':False}
        inv[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
    proc = subprocess.run(
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'scripts/devtool', '-p', 'test_ui_d02.py', '-q'],
        cwd=ROOT, capture_output=True, text=True, timeout=90
    ) if source['overall']=='PASS_SOURCE_CONTRACT' else None
    passed = proc is not None and proc.returncode == 0
    return {
        'schema_version':1, 'producer':'cinderbox-ui-d02-devtool',
        'overall': 'PASS_HOST_SOURCE' if passed else 'FAILED_HOST_SOURCE',
        'source_commit': os.environ.get('GITHUB_SHA',''), 'source_sha256': dict(sorted(inv.items())),
        'checks': source['checks'], 'host_tests': 'PASS' if passed else ('FAILED' if proc else 'NOT_RUN'),
        'android_build':'NOT_RUN', 'device_tests':'NOT_RUN',
        'historical_m21_results_replaced':False,'release_qualified':False,'publication_allowed':False,
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args=parser.parse_args()
    try:
        result=produce()
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        result={'schema_version':1,'producer':'cinderbox-ui-d02-devtool','overall':'BLOCKED_HOST_GATE','error_class':type(exc).__name__,'release_qualified':False,'publication_allowed':False}
    raw=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(raw, encoding='utf-8')
    print(raw,end='')
    return 0 if result['overall']=='PASS_HOST_SOURCE' else 1

if __name__ == '__main__':
    raise SystemExit(main())
