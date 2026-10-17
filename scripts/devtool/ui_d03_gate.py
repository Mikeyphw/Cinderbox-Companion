#!/usr/bin/env python3
"""One UI-D03 gate reused unchanged by Devtool workflows and both GitHub Actions flows."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from ui_d03_source import verify,ROOT

REQUIRED = (
    '.devtool.toml', 'scripts/devtool/ui_d03_source.py',
    'scripts/devtool/ui_d03_gate.py', 'scripts/devtool/test_ui_d03.py',
    'scripts/devtool/ui_d03_device_capture.py',
    'app/src/androidTest/java/com/sdvsync/qualification/EarthyD03AccessibilityDeviceTest.kt',
    'docs/security/M3_RELEASE_POLICY.json',
)

def produce() -> dict:
    source=verify()
    inv=dict(source['source_sha256'])
    for rel in REQUIRED:
        path=ROOT/rel
        if not path.is_file() or path.is_symlink():
            return {'schema_version':1,'overall':'BLOCKED_SOURCE_MISSING','missing':rel,
                    'release_qualified':False,'publication_allowed':False}
        inv[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
    proc=subprocess.run([sys.executable,'-m','unittest','discover','-s','scripts/devtool',
                          '-p','test_ui_d03.py','-q'],cwd=ROOT,text=True,capture_output=True,timeout=90) if source['overall']=='PASS_HOST_STATIC' else None
    return {
        'schema_version':1,'producer':'cinderbox-ui-d03-devtool',
        'overall':'PASS_HOST_SOURCE' if proc is not None and proc.returncode==0 else 'FAILED_HOST_SOURCE',
        'source_commit':os.getenv('GITHUB_SHA',''),
        'source_sha256':dict(sorted(inv.items())),
        'checks':source['checks'],'contrast_ratios':source['contrast_ratios'],
        'host_tests':'PASS' if proc and proc.returncode==0 else 'FAILED_OR_NOT_RUN',
        'android_build':'NOT_RUN', 'device_tests':'NOT_RUN','screenshots':'NOT_CAPTURED',
        'historical_m21_results_replaced':False,'release_qualified':False,'publication_allowed':False,
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try: result=produce()
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        result={'schema_version':1,'producer':'cinderbox-ui-d03-devtool',
                'overall':'BLOCKED_HOST_GATE','error_class':type(exc).__name__,
                'release_qualified':False,'publication_allowed':False}
    raw=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(raw,encoding='utf-8')
    print(raw,end='')
    return 0 if result['overall']=='PASS_HOST_SOURCE' else 1

if __name__=='__main__':raise SystemExit(main())
