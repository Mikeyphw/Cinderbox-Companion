#!/usr/bin/env python3
"""Explicit synthetic UI screenshots only; no installs, permissions, reboots or account access."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
NAMES=('cinderbox-ui-d03-earthy-light-320dp-fs160.png',
       'cinderbox-ui-d03-earthy-dark-320dp-fs160.png')
TEST_CLASS='com.sdvsync.qualification.EarthyD03AccessibilityDeviceTest'
RUNNER='com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner'

def png_size(data:bytes):
    if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data)<24:
        raise ValueError('invalid screenshot PNG signature')
    return struct.unpack('>II',data[16:24])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-synthetic-device-tests',action='store_true',required=True)
    p.add_argument('--output-dir',required=True,type=Path)
    p.add_argument('--serial',help='explicit adb serial for multiple attached devices')
    p.add_argument('--ci-run-id',help='CI run provenance label (not installed APK attestation)')
    args=p.parse_args()
    adb=['adb']+(['-s',args.serial] if args.serial else [])
    def cmd(*parts):
        return subprocess.run(adb+list(parts),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
    def checked(*parts):
        result=cmd(*parts)
        if result.returncode!=0: raise RuntimeError('adb command failed: '+' '.join(parts))
        return result.stdout
    result={'schema_version':1,'producer':'cinderbox-ui-d03-synthetic-device',
            'overall':'BLOCKED', 'source':'local_checkout','ci_run_id_label':args.ci_run_id,
            'installed_apk_source_verified':False,'real_app_screenshots':False,
            'historical_m21_results_replaced':False,'release_qualified':False,'publication_allowed':False}
    try:
        source=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,timeout=10)
        result['source_commit']=source.stdout.strip() if source.returncode==0 else ''
        devices=checked('devices').decode('utf-8','replace')
        connected=[line for line in devices.splitlines()[1:] if line.strip().endswith('\tdevice')]
        if args.serial is None and len(connected)!=1:raise RuntimeError('exactly one authorized adb device required, or use --serial')
        checked('shell','pm','path','com.sdvsync.test')
        checked('shell','run-as','com.sdvsync','id')
        instrument=cmd('shell','am','instrument','-w','-r','-e','class',TEST_CLASS,RUNNER)
        output=instrument.stdout.decode('utf-8','replace')
        if instrument.returncode!=0 or 'OK (4 tests)' not in output or 'FAILURES!!!' in output:
            raise RuntimeError('four-case synthetic Compose instrumentation did not PASS')
        result['instrumentation']='PASS_4_SYNTHETIC_TESTS'
        args.output_dir.mkdir(parents=True,exist_ok=True)
        images=[]
        for name in NAMES:
            content=checked('exec-out','run-as','com.sdvsync','cat','files/'+name)
            width,height=png_size(content)
            if width<320 or height<100: raise RuntimeError('unexpected screenshot dimensions')
            dest=args.output_dir/name
            dest.write_bytes(content)
            images.append({'filename':name,'width_px':width,'height_px':height,
                           'sha256':hashlib.sha256(content).hexdigest()})
        result.update(overall='PASS_SYNTHETIC_UI_UNBOUND',screenshots=images,
                      screenshot_count=len(images))
    except (OSError,RuntimeError,subprocess.TimeoutExpired,ValueError) as exc:
        result['error_class']=type(exc).__name__
        result['error_summary']=str(exc)[:200]
    finally:
        args.output_dir.mkdir(parents=True,exist_ok=True)
        (args.output_dir/'ui-d03-device-evidence.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result['overall']=='PASS_SYNTHETIC_UI_UNBOUND' else 1

if __name__=='__main__':raise SystemExit(main())
