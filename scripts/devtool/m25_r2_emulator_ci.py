#!/usr/bin/env python3
"""Four fixed R2 tests plus one synthetic screenshot on the R48-owned API36 emulator."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from m25_emulator_ci import inspect_emulator, validate_identity, command
from r47_capture import png_dimensions

TEST_CLASS='com.sdvsync.mods.update.M25R2UpdateInsightDeviceTest'
TEST_PACKAGE='com.sdvsync.test'
RUNNER='androidx.test.runner.AndroidJUnitRunner'
TESTS=(
    'showsAllStatusesAtCompactFontScaleAndCapturesPreview',
    'parserNeverClaimsCurrentForAbsentSuggestedVersion',
    'parserRejectsDuplicateAndUnknownRemoteIds',
    'changelogAndFreshnessAreInertAndBounded',
)
PNG='m25-r2-status-320dp-fs160.png'
RECEIPT='M25_R2_EMULATOR_EVIDENCE.json'

def summarize(output: str, code: int) -> dict:
    events={name: [] for name in TESTS}
    unknown=False
    active=None
    terminal=[]
    for line in output.splitlines():
        if line.startswith('INSTRUMENTATION_STATUS: test='):
            name=line.partition('=')[2].strip()
            if active is not None:unknown=True
            active=name if name in TESTS else None
            if active is None:unknown=True
        elif line.startswith('INSTRUMENTATION_STATUS_CODE: '):
            status=line.partition(': ')[2].strip()
            if active is not None:events[active].append(status)
            else:unknown=True
            active=None
        elif line.startswith('INSTRUMENTATION_CODE: '):
            terminal.append(line.partition(': ')[2].strip())
    return {
        'expected_tests':list(TESTS),
        'started_tests':[x for x in TESTS if events[x] and events[x][0]=='1'],
        'passed_tests':[x for x in TESTS if events[x]==['1','0']],
        'exact_sequence': all(v==['1','0'] for v in events.values()),
        'unknown_test_present': unknown,
        'terminal_success': terminal==['-1'],
        'reported_ok': bool(re.search(r'(?m)^OK \(4 tests\)\s*$',output)),
        'error_categories':[name for name,needles in {
            'crash':('Process crashed','INSTRUMENTATION_FAILED','shortMsg='),
            'abort':('INSTRUMENTATION_ABORTED',),
            'assertion':('AssertionError','AssertionFailedError','ComparisonFailure'),
        }.items() if any(value in output for value in needles)],
        'exit_zero':code==0,
        'raw_logs_retained':False,
    }

def accepted(s:dict)->bool:
    return bool(s['started_tests']==list(TESTS) and s['passed_tests']==list(TESTS)
        and s['exact_sequence'] and not s['unknown_test_present']
        and s['terminal_success'] and s['reported_ok'] and s['exit_zero']
        and s['error_categories']==[] and s['raw_logs_retained'] is False)

def execute(output:Path,identity_path:Path)->bool:
    output.mkdir(parents=True,exist_ok=True)
    sha=os.environ.get('GITHUB_SHA','');run_id=os.environ.get('GITHUB_RUN_ID','')
    evidence={
        'schema_version':1,'producer':'cinderbox-m25-r2-hosted-ui',
        'overall':'REFUSED','source_sha':sha,'run_id':run_id,
        'test_class':TEST_CLASS,'test_count':len(TESTS),'android_api':36,
        'hosted_emulator_only':True,'physical_device_qualified':False,
        'release_qualified':False,'publication_allowed':False,
        'automatic_installation':False,'raw_logs_retained':False,
    }
    screenshot=output/PNG
    screenshot.unlink(missing_ok=True)
    try:
        if not re.fullmatch('[0-9a-f]{40}',sha) or not re.fullmatch('[0-9]+',run_id):
            raise RuntimeError('source or run identity invalid')
        if os.environ.get('RUNNER_OS')!='Linux' or command('uname','-m')!='x86_64':
            raise RuntimeError('unsupported host')
        if command('git','rev-parse','HEAD')!=sha:
            raise RuntimeError('source not pinned')
        identity=validate_identity(identity_path,sha)
        inspect_emulator('emulator-5554')
        adb=['adb','-s','emulator-5554']
        raw=subprocess.run(adb+['shell','am','instrument','-w','-r','-e','class',TEST_CLASS,
                                TEST_PACKAGE+'/'+RUNNER],capture_output=True,text=True,timeout=300)
        summary=summarize(raw.stdout,raw.returncode)
        evidence['summary']=summary
        evidence['app_apk_sha256']=identity['app_apk_sha256']
        evidence['android_test_apk_sha256']=identity['android_test_apk_sha256']
        if not accepted(summary): raise RuntimeError('instrumentation did not pass')
        fetched=subprocess.run(adb+['exec-out','run-as','com.sdvsync','cat','files/'+PNG],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
        image=fetched.stdout
        if fetched.returncode or len(image)>4_000_000 or len(image)<1000:
            raise RuntimeError('private synthetic screenshot unavailable')
        width,height=png_dimensions(image)
        if width<320 or height<200:raise RuntimeError('screenshot dimensions invalid')
        screenshot.write_bytes(image)
        evidence['screenshot']={'name':PNG,'sha256':hashlib.sha256(image).hexdigest(),
            'bytes':len(image),'width':width,'height':height}
        evidence['overall']='PASS_M25_R2_HOSTED_EMULATOR'
        print('M25_R2_API36_4_TESTS_1_SCREENSHOT_PASS')
        return True
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError,AssertionError,KeyError,TypeError):
        screenshot.unlink(missing_ok=True)
        print('M25_R2_EMULATOR_REFUSED',file=sys.stderr)
        return False
    finally:
        (output/RECEIPT).write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument('--output-dir',required=True,type=Path)
    p.add_argument('--r48-identity',required=True,type=Path)
    args=p.parse_args()
    return 0 if execute(args.output_dir,args.r48_identity) else 1

if __name__=='__main__':raise SystemExit(main())
