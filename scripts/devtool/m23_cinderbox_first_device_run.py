#!/usr/bin/env python3
"""Run only the 3 new Cinderbox-first app-cache Android cases; never install APKs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
from m14_device_qualification import parse_instrumentation, DeviceGateError

CLASS = 'com.sdvsync.qualification.M23CinderboxFirstDeviceTest'
RUNNER = 'com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner'
METHODS = (
    'm23cb_01ImportedMainGameDoesNotBlockSeparateDestination',
    'm23cb_02AllPrimaryCinderboxSubtreesProtected',
    'm23cb_03UnsafeAliasAndPartialDownloadFailClosed',
)
IDS = ('m23cb_01', 'm23cb_02', 'm23cb_03')

def parse(raw):
    try:
        summary = parse_instrumentation(raw, frozenset(METHODS))
    except DeviceGateError as exc:
        if exc.case_summary:
            exc.case_summary['cases'] = dict(zip(IDS,
                [exc.case_summary['cases'][m] for m in METHODS]))
        raise
    summary['cases'] = dict(zip(IDS, [summary['cases'][m] for m in METHODS]))
    return summary

def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', help='Explicit ADB serial; required if multiple targets')
    parser.add_argument('--execute-synthetic-tests', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ci-run-id', type=int, help='Label only; installed APK provenance NOT checked')
    args = parser.parse_args()
    doc = dict(schema_version=1, producer='cinderbox-m23-primary-app-synthetic-device',
               overall='FAILED_OR_BLOCKED', expected_cases=3, completed=0,
               cases={k:'NOT_COMPLETED' for k in IDS}, ci_run_id_label=args.ci_run_id,
               installed_source_verified=False, real_cinderbox_installation_examined=False,
               real_user_files_modified=False, automatic_apk_install=False,
               automatic_data_clear=False, historical_evidence_replaced=False,
               device_qualified=False, release_qualified=False, publication_allowed=False)
    adb = ['adb'] + (['-s',args.serial] if args.serial else [])
    def command(*cmd, timeout=40):
        p = subprocess.run(adb+list(cmd), text=True, capture_output=True, timeout=timeout)
        if p.returncode: raise RuntimeError('ADB_COMMAND_FAILED')
        return p.stdout
    try:
        connected = [items[0] for line in command('devices').splitlines()[1:]
                     if len(items:=line.split()) == 2 and items[1] == 'device']
        if args.serial:
            if args.serial not in connected: raise RuntimeError('SELECTED_DEVICE_UNAVAILABLE')
        elif len(connected) != 1:
            raise RuntimeError('EXPLICIT_SERIAL_REQUIRED_FOR_MULTIPLE_DEVICES')
        for package in ('com.sdvsync','com.sdvsync.test'):
            if 'package:' not in command('shell','pm','path',package):
                raise RuntimeError('BOTH_APKS_MUST_BE_INSTALLED')
        results = parse(command('shell','am','instrument','-w','-r','-e','class',CLASS,RUNNER,timeout=900))
        doc.update(overall='PASS_3_CINDERBOX_FIRST_SYNTHETIC_UNBOUND',
                   completed=results['completed'],cases=results['cases'])
    except DeviceGateError as exc:
        doc['failure_code'] = exc.code
        if exc.case_summary:
            doc.update(completed=exc.case_summary['completed'],cases=exc.case_summary['cases'])
    except (RuntimeError,OSError,subprocess.TimeoutExpired) as exc:
        doc['failure_code'] = str(exc)[:80] if isinstance(exc,RuntimeError) else type(exc).__name__
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.is_symlink():
        print('Unsafe report destination',file=sys.stderr);return 1
    args.output.write_text(json.dumps(doc,indent=2,sort_keys=True)+'\n')
    print(json.dumps(doc,sort_keys=True,indent=2))
    return 0 if doc['overall']=='PASS_3_CINDERBOX_FIRST_SYNTHETIC_UNBOUND' else 1
if __name__=='__main__':raise SystemExit(run())
