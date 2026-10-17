#!/usr/bin/env python3
"""Explicit no-install M23 synthetic Android instrumentation runner (private fixtures only)."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from m14_device_qualification import parse_instrumentation, DeviceGateError
from m23_device_test_gate import CLASS,EXPECTED

RUNNER='com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-synthetic-tests',required=True,action='store_true')
    p.add_argument('--serial',help='Explicit adb serial for multiple devices')
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--ci-run-id',type=int,help='Run label only; does not attest installed packages')
    args=p.parse_args()
    report=dict(schema_version=1,producer='cinderbox-m23-private-synthetic-device',
                overall='INCOMPLETE',expected_cases=len(EXPECTED),
                cases={name:'NOT_RUN' for name in EXPECTED},
                ci_run_id_label=args.ci_run_id,installed_source_verified=False,
                real_game_installation_examined=False,real_storage_permissions_qualified=False,
                automatic_apk_install=False,automatic_reboot=False,automatic_data_clear=False,
                historical_m14_m22_evidence_replaced=False,device_qualified=False,
                release_qualified=False,publication_allowed=False)
    adb=['adb']+(['-s',args.serial] if args.serial else [])
    def command(*tokens,timeout=40):
        p=subprocess.run(adb+list(tokens),capture_output=True,text=True,timeout=timeout,check=False)
        if p.returncode:raise RuntimeError('ADB_PRECONDITION_FAILED')
        return p.stdout
    try:
        connected=[line.split()[0] for line in command('devices').splitlines()[1:]
                   if len(line.split())==2 and line.split()[1]=='device']
        if args.serial:
            if args.serial not in connected:raise RuntimeError('SELECTED_DEVICE_UNAVAILABLE')
        elif len(connected)!=1:
            raise RuntimeError('EXACTLY_ONE_ADB_DEVICE_REQUIRED_OR_EXPLICIT_SERIAL')
        for package in ('com.sdvsync','com.sdvsync.test'):
            if 'package:' not in command('shell','pm','path',package):
                raise RuntimeError('APP_AND_TEST_APKS_REQUIRED')
        output=command('shell','am','instrument','-w','-r','-e','class',CLASS,RUNNER,timeout=900)
        status=parse_instrumentation(output,frozenset(EXPECTED))
        report.update(overall='PASS_10_SYNTHETIC_DEVICE_TESTS_UNBOUND',
                      completed=status['completed'],cases=status['cases'])
    except DeviceGateError as exc:
        report['failure_code']=exc.code
        if exc.case_summary:
            report.update(completed=exc.case_summary['completed'],cases=exc.case_summary['cases'])
        report['overall']='FAILED_OR_BLOCKED'
    except (RuntimeError, OSError,subprocess.TimeoutExpired) as exc:
        report['failure_code']=str(exc)[:80] if isinstance(exc,RuntimeError) else type(exc).__name__
        report['overall']='FAILED_OR_BLOCKED'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.is_symlink():
        print('Unsafe output destination',file=sys.stderr);return 1
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0 if report['overall']=='PASS_10_SYNTHETIC_DEVICE_TESTS_UNBOUND' else 1
if __name__=='__main__':raise SystemExit(main())
