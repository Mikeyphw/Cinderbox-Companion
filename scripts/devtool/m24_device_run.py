#!/usr/bin/env python3
"""Explicitly run four M24 app-private Android fixtures. Never downloads or installs."""
import argparse, json, subprocess, sys
from pathlib import Path
from m14_device_qualification import parse_instrumentation, DeviceGateError
CLASS="com.sdvsync.qualification.M24SteamDownloadSafetyDeviceTest"
METHODS=("m24_01AuthenticatedBranchBuildGateFailClosed",
         "m24_02FreshCheckpointCannotResumeWithoutBuild",
         "m24_03BoundBuildSurvivesColdRecovery",
         "m24_04DriftLeavesOwnedPartialBytesUntouched")
IDS=tuple(f"m24_{n:02d}" for n in range(1,5))

def parse(raw):
    try: outcome=parse_instrumentation(raw,frozenset(METHODS))
    except DeviceGateError as e:
        if e.case_summary:
            e.case_summary['cases']={k:e.case_summary['cases'][method] for k,method in zip(IDS,METHODS)}
        raise
    outcome['cases']={k:outcome['cases'][method] for k,method in zip(IDS,METHODS)}
    return outcome

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--execute-synthetic-tests',action='store_true',required=True)
    ap.add_argument('--serial')
    ap.add_argument('--ci-run-id',type=int)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    doc=dict(schema_version=1,producer='cinderbox-m24-private-device',
             overall='FAILED_OR_BLOCKED',completed=0,expected_cases=4,
             cases=dict.fromkeys(IDS,'NOT_COMPLETED'),ci_run_id_label=args.ci_run_id,
             authenticated_steam_tested=False,live_download_performed=False,
             installed_source_verified=False,real_cinderbox_game_modified=False,
             automatic_install=False,automatic_data_clear=False,
             historical_m14_m23_evidence_replaced=False,device_qualified=False,
             release_qualified=False,publication_allowed=False)
    adb=['adb']+(['-s',args.serial] if args.serial else [])
    def cmd(*parts,timeout=50):
        proc=subprocess.run(adb+list(parts),capture_output=True,text=True,timeout=timeout)
        if proc.returncode:raise RuntimeError('ADB_COMMAND_FAILED')
        return proc.stdout
    try:
        targets=[s[0] for l in cmd('devices').splitlines()[1:]
                 if len(s:=l.split())==2 and s[1]=='device']
        if args.serial and args.serial not in targets:raise RuntimeError('SELECTED_DEVICE_UNAVAILABLE')
        if not args.serial and len(targets)!=1:raise RuntimeError('EXPLICIT_SERIAL_REQUIRED')
        for package in ('com.sdvsync','com.sdvsync.test'):
            if 'package:' not in cmd('shell','pm','path',package):raise RuntimeError('M24_APKS_NOT_INSTALLED')
        result=parse(cmd('shell','am','instrument','-w','-r','-e','class',CLASS,
                         'com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner',timeout=900))
        doc.update(overall='PASS_4_M24_PRIVATE_FIXTURES_UNBOUND',completed=result['completed'],cases=result['cases'])
    except DeviceGateError as e:
        doc['failure_code']=e.code
        if e.case_summary:doc.update(completed=e.case_summary['completed'],cases=e.case_summary['cases'])
    except (RuntimeError,OSError,subprocess.TimeoutExpired) as e:
        doc['failure_code']=str(e)[:80] if isinstance(e,RuntimeError) else type(e).__name__
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.is_symlink():print('Unsafe output path',file=sys.stderr);return 1
    args.output.write_text(json.dumps(doc,indent=2,sort_keys=True)+'\n')
    print(json.dumps(doc,indent=2,sort_keys=True))
    return 0 if doc['overall']=='PASS_4_M24_PRIVATE_FIXTURES_UNBOUND' else 1
if __name__=='__main__':raise SystemExit(main())
