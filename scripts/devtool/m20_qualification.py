#!/usr/bin/env python3
"""M20: exactly 52 Android scenarios, eight independently runnable source-bound lanes.

One M20-only CI instrumentation APK, explicit consent, zero old device reruns.
C lane is a genuine force-stop after a debug synthetic worker has written bytes.
Never pm clear, uninstall, reboot, alter Steam data, or publish. No raw stacks.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import secrets
import sys
import tempfile
import time

import m14_device_qualification as m14

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=Path(__file__).with_name('m20_scenarios.json')
REPO=m14.REPO
BRANCH='feature/m20-consolidated-resilience'
CI_STEP='M20 consolidated 52-scenario host regressions'
SUCCESS='PASS_CONSOLIDATED_M20_RESILIENCE_AUTOMATION'
MAINT_CLASS='com.sdvsync.qualification.M20FixtureMaintenanceDeviceTest'


def matrix():
    data=json.loads(MANIFEST.read_text(encoding='utf8'))
    lanes=data['lanes']
    assert set(lanes)==set('ABCDEFGH')
    assert [len(lanes[k]['cases']) for k in 'ABCDEFGH']==[8,7,8,7,6,6,5,5]
    all_names=[name for lane in lanes.values() for name in lane['cases']]
    assert len(all_names)==52 and len(set(all_names))==52
    assert all(re.fullmatch(r'[a-h]\d{2}[A-Za-z0-9]+',name) for name in all_names)
    return lanes


def require(yes,code): m14.require(yes,code)


def source_identity(repo):
    head=m14.git_head(repo)
    tracked=['scripts/devtool/m14_device_qualification.py',
             'scripts/devtool/m20_qualification.py','scripts/devtool/m20_scenarios.json',
             'app/src/androidTest/java/com/sdvsync/qualification/M20ConsolidatedDeviceTest.kt',
             'app/src/androidTest/java/com/sdvsync/qualification/M20OwnedFixtures.kt',
             'app/src/debug/java/com/sdvsync/qualification/M20SyntheticWorkerService.kt']
    require(not m14.command(['git','-C',str(repo),'status','--porcelain','--',*tracked]).strip(),
            'LOCAL_QUALIFIER_MODIFIED')
    require(m14.SHA40.fullmatch(head) is not None,'M20_SOURCE_INVALID')
    return head


def verify_ci(run,jobs,head):
    m14.verify_ci(run,jobs,head)
    require(run.get('head_branch') in (BRANCH,'master'),'M20_CI_BRANCH_MISMATCH')
    steps=[s for j in jobs.get('jobs',[]) for s in j.get('steps',[])]
    require(any(s.get('name')==CI_STEP and s.get('conclusion')=='success' for s in steps),
            'M20_HOST_CI_INCOMPLETE')


def diagnostic(raw, case):
    """Only classify the failed instrumentation *event for this case*.

    AndroidJUnitRunner emits status key/value records in an arbitrary order
    followed by STATUS_CODE; multiline stack continuations belong to that
    event. Never search an entire multi-case batch for a source line: it
    incorrectly attributes another test's failure to this case.
    """
    event=[]
    for line in raw.splitlines():
        if not line.startswith('INSTRUMENTATION_STATUS_CODE:'):
            event.append(line)
            continue
        code=line.split(':',1)[1].strip()
        current=[x.partition('=')[2].strip() for x in event
                 if x.startswith('INSTRUMENTATION_STATUS: test=')]
        if case in current and code in ('-2','-1'):
            block='\n'.join(event)
            match=re.search(r'(?m)^INSTRUMENTATION_STATUS: stack=',block)
            stack=block[match.end():] if match else ''
            next_status=re.search(r'(?m)^INSTRUMENTATION_STATUS:',stack)
            if next_status: stack=stack[:next_status.start()]
            category='ASSERTION_FAILED' if 'AssertionError' in stack else 'TEST_EXCEPTION'
            if 'SecurityException' in stack: category='ANDROID_SECURITY_RESTRICTION'
            elif 'ForegroundServiceStartNotAllowedException' in stack:
                category='ANDROID_FOREGROUND_START_RESTRICTED'
            elif 'NoSuchMethodException' in stack: category='FRAMEWORK_REFLECTION_FAILURE'
            elif 'M20_FIXTURE_' in stack or 'M20_CANONICAL_' in stack:
                category='OWNED_FIXTURE_SAFETY_GUARD'
            location=re.search(r'M20ConsolidatedDeviceTest\.kt:(\d{1,5})\b',stack)
            return {'category':category,'source_line':int(location.group(1)) if location else None}
        event=[]
    return {'category':'INSTRUMENTATION_FAILED','source_line':None}


def pid(device):
    raw=device.shell('sh','-c','pidof com.sdvsync || true',timeout=15).strip()
    require(not raw or re.fullmatch(r'[0-9]+(?:\s+[0-9]+)*',raw),'M20_PID_INVALID')
    return tuple(raw.split())


def launch(device):
    text=device.launch()
    require(re.search(r'(?m)^Status:\s*ok\s*$',text) and
            re.search(r'(?m)^Activity:\s*com\.sdvsync/\.MainActivity\s*$',text),
            'M20_LAUNCH_FAILED')
    require(bool(pid(device)),'M20_APP_NOT_STARTED')


def arm_live_worker_before_force_stop(device, nonce):
    """Re-establish the debug worker after AndroidJUnitRunner's lifecycle teardown.

    An instrumentation PASS says c07 seeded its owned fixture, NOT that the app
    process remains alive after the test process exits.  Android can terminate
    that process at the test boundary. We explicitly launch the app and start
    the existing non-exported, debug-only worker via the explicitly selected
    privileged device transport, then require a live foreground ServiceRecord.
    No operation touches production Steam, mods, saves, or external storage.
    """
    require(re.fullmatch(r'[0-9a-f]{32}', nonce) is not None, 'M20_WORKER_NONCE_INVALID')
    launch(device)
    before = pid(device)
    require(bool(before), 'M20_PRE_STOP_PROCESS_ABSENT')
    result = device.shell('am', 'start-foreground-service', '-n',
        'com.sdvsync/.qualification.M20SyntheticWorkerService',
        '--es', 'case_id', 'c07SeedRunningWorkerBeforeForceStop',
        '--es', 'nonce', nonce, timeout=30)
    require('Starting service:' in result and 'Error:' not in result,
            'M20_DEBUG_WORKER_REARM_FAILED')
    # Inspect service state only in memory. Never copy a dumpsys receipt into
    # published evidence because its other entries may contain private data.
    for probe in range(2):
        # Two time-separated probes prevent a transient service-start receipt
        # from being mistaken for a continuously active synthetic worker.
        if probe:
            time.sleep(0.3)
        state = device.shell('dumpsys', 'activity', 'services', 'com.sdvsync', timeout=30)
        service = re.search(
            r'(?m)^\s*\*?\s*ServiceRecord\{[^\n]*'
            r'com\.sdvsync/\.qualification\.M20SyntheticWorkerService[^\n]*',
            state)
        require(service is not None, 'M20_DEBUG_WORKER_NOT_RUNNING')
        remainder = state[service.end():]
        next_service = re.search(r'(?m)^\s*\*?\s*ServiceRecord\{', remainder)
        owned_state = remainder[:next_service.start() if next_service else len(remainder)]
        require(re.search(r'\bapp=ProcessRecord\{[^\n]*com\.sdvsync', owned_state)
                is not None, 'M20_DEBUG_WORKER_NO_LIVE_PROCESS')
        after = pid(device)
        require(bool(after) and after == before, 'M20_DEBUG_WORKER_PROCESS_CHANGED')


def instrument(device,klass,method,nonce,expect):
    suffix='#'+method if method else ''
    raw=device.shell('am','instrument','-w','-r',
                     '-e','class',klass+suffix,
                     '-e','m20_nonce',nonce,m14.RUNNER,timeout=900)
    try:
        return m14.parse_instrumentation(raw,frozenset(expect))
    except m14.DeviceGateError as error:
        # Carry only allowlisted summaries. No stack, path, nonce, or credentials.
        error.m20_diagnostic={name:diagnostic(raw,name) for name in expect
                              if error.case_summary and
                              error.case_summary.get('cases',{}).get(name)!='PASS'}
        raise


def new_report(run_id,transport,selection,head=None):
    lanes=matrix()
    return dict(schema_version=1,producer='cinderbox-m20-consolidated-device',
                repository=REPO,source_commit=head,runner_source_commit=head,
                github_run_id=run_id,ci_checkout_commit=None,ci_checkout_ref=None,
                ci='NOT_RUN',install='NOT_RUN',transport=transport,device=None,
                apk_sha256=None,test_apk_sha256=None,lanes_requested=selection,
                lanes={k:dict(status='NOT_RUN',cases={name:'NOT_RUN' for name in v['cases']})
                       for k,v in lanes.items()},
                force_stop='NOT_RUN',process_gone='NOT_RUN',cold_relaunch='NOT_RUN',
                fixture_inventory='AVAILABLE_SEPARATELY',
                failure_code=None,failure_diagnostics={},overall='INCOMPLETE',
                release_qualified=False,publication_allowed=False,device_qualified=False,
                automatic_uninstall=False,automatic_data_clear=False,automatic_reboot=False,
                m14_reexecuted=False,m15_reexecuted=False,m17_reexecuted=False,
                m18_reexecuted=False,m19_reexecuted=False)


def store(path,report):
    m14.write_report(path,report)
    print(json.dumps({'overall':report['overall'],'failure_code':report['failure_code'],
                      'report':str(path)},sort_keys=True))


def execute(args):
    available=matrix()
    if args.all:
        selection=list('ABCDEFGH')
    elif args.all_safe_lanes:
        selection=list('ABDEFGH')
    else:
        selection=list(dict.fromkeys(x.strip().upper() for x in args.lane.split(',')))
    report=new_report(args.run_id,args.transport,selection)
    try:
        require(selection and set(selection)<=set(available),'M20_INVALID_LANE_SELECTION')
        require(args.install and args.allow_replace,'M20_INSTALL_EXPLICIT_CONSENT_REQUIRED')
        require(args.ui_opt_in and args.test_profile_opt_in,'M20_SIGNED_OUT_UI_CONSENT_REQUIRED')
        require('C' not in selection or args.force_stop_opt_in,'M20_FORCE_STOP_CONSENT_REQUIRED')
        repo=args.repo.resolve()
        head=source_identity(repo)
        report.update(source_commit=head,runner_source_commit=head)
        require(args.run_id>0,'M20_RUN_ID_INVALID')
        run=m14.json_from_gh([f'repos/{REPO}/actions/runs/{args.run_id}'])
        jobs=m14.json_from_gh([f'repos/{REPO}/actions/runs/{args.run_id}/jobs?per_page=100'])
        verify_ci(run,jobs,head)
        with tempfile.TemporaryDirectory(prefix='cinderbox-m20-') as tmp:
            temp=Path(tmp);main=temp/'main';test=temp/'test';main.mkdir();test.mkdir()
            m14.command(['gh','run','download',str(args.run_id),'--repo',REPO,
                         '--name','debug-apk','--dir',str(main)],timeout=240)
            m14.command(['gh','run','download',str(args.run_id),'--repo',REPO,
                         '--name','m14-androidtest-apk','--dir',str(test)],timeout=240)
            provenance=m14.read_json(main/'M3_PROVENANCE.json')
            commit,ref=m14.verified_ci_checkout(run,head,
                artifact_commit=provenance.get('source_commit'),
                artifact_ref=provenance.get('source_ref'))
            main_apk,test_apk,digest,test_digest=m14.verify_artifacts(
                main,test,commit,source_ref=ref,run_id=args.run_id)
            report.update(ci='PASS',ci_checkout_commit=commit,ci_checkout_ref=ref,
                          apk_sha256=digest,test_apk_sha256=test_digest)
            device=m14.Transport(args.transport)
            report['device']=device.device_info()
            report['install']='ATTEMPTED'
            main_installed=device.installed(m14.PACKAGE)
            test_installed=device.installed(m14.TEST_PACKAGE)
            require('Success' in device.install(main_apk,replace=main_installed).splitlines(),
                    'M20_APP_INSTALL_FAILED')
            require('Success' in device.install(test_apk,replace=test_installed,test=True).splitlines(),
                    'M20_TEST_INSTALL_FAILED')
            require(device.installed(m14.PACKAGE) and device.installed(m14.TEST_PACKAGE),
                    'M20_INSTALL_NOT_VERIFIED')
            report['install']='PASS'
            nonce=secrets.token_hex(16)
            # Use full class per normal lane, C stages explicitly separated.
            for lane in selection:
                spec=available[lane]
                report['lanes'][lane]['status']='RUNNING'
                if lane!='C':
                    result=instrument(device,spec['class'],None,nonce,spec['cases'])
                    report['lanes'][lane].update(status='PASS',cases=result['cases'])
                else:
                    for case in spec['cases'][:-1]:
                        result=instrument(device,spec['class'],case,nonce,[case])
                        report['lanes']['C']['cases'][case]='PASS'
                    # Instrumentation teardown is allowed to stop the app. The
                    # c07 PASS is durable fixture evidence, not live-PID proof.
                    # Arm and verify the non-exported debug worker in a live app
                    # process before issuing the destructive force-stop.
                    arm_live_worker_before_force_stop(device, nonce)
                    report['force_stop']='ATTEMPTED'
                    device.shell('am','force-stop',m14.PACKAGE,timeout=30)
                    report['force_stop']='PASS'
                    require(not pid(device),'M20_PROCESS_SURVIVED_FORCE_STOP')
                    report['process_gone']='PASS'
                    report['cold_relaunch']='ATTEMPTED'
                    launch(device)
                    report['cold_relaunch']='PASS'
                    case=spec['cases'][-1]
                    result=instrument(device,spec['class'],case,nonce,[case])
                    report['lanes']['C']['cases'][case]='PASS'
                    report['lanes']['C']['status']='PASS'
            if all(report['lanes'][k]['status']=='PASS' for k in selection):
                report['overall']=SUCCESS if set(selection)==set(available) else 'PASS_SELECTED_M20_LANES'
    except m14.DeviceGateError as e:
        report.update(overall='FAILED_OR_BLOCKED',failure_code=e.code)
        # Host-side lifecycle faults also fail the active lane. Otherwise a
        # failed real-device campaign can misleadingly leave lane C RUNNING.
        failing_lane=next((k for k in selection if report['lanes'][k]['status']=='RUNNING'),None)
        if failing_lane:
            report['lanes'][failing_lane]['status']='FAILED_OR_BLOCKED'
            if getattr(e,'case_summary',None):
                for name,value in e.case_summary.get('cases',{}).items():
                    report['lanes'][failing_lane]['cases'][name]=value
                report['failure_diagnostics']=getattr(e,'m20_diagnostic',{})
    except Exception:
        report.update(overall='FAILED_OR_BLOCKED',failure_code='UNEXPECTED_FAILURE')
    store(args.output,report)
    return 0 if report['overall'] in (SUCCESS,'PASS_SELECTED_M20_LANES') else 1


def merge(args):
    lanes=matrix()
    result=new_report(None,None,list(lanes))
    try:
        require(len(args.merge_reports)>=2,'M20_MERGE_NEEDS_MULTIPLE_REPORTS')
        docs=[m14.read_json(Path(s)) for s in args.merge_reports]
        base=docs[0]
        keys=('repository','source_commit','runner_source_commit','github_run_id',
              'ci_checkout_commit','ci_checkout_ref','apk_sha256','test_apk_sha256','device','transport')
        require(base.get('ci')=='PASS' and base.get('install')=='PASS',
                'M20_MERGE_UNQUALIFIED_INPUT')
        for doc in docs:
            require(all(doc.get(k)==base.get(k) for k in keys),'M20_MERGE_SOURCE_MISMATCH')
            require(doc.get('producer')=='cinderbox-m20-consolidated-device' and
                    doc.get('failure_code') is None and
                    doc.get('overall') in ('PASS_SELECTED_M20_LANES',SUCCESS),
                    'M20_MERGE_FAILURE_INPUT')
        result.update({k:base.get(k) for k in keys})
        result['ci']='PASS';result['install']='PASS'
        selected=set()
        for doc in docs:
            for lane in doc.get('lanes_requested',[]):
                require(lane in lanes and lane not in selected,'M20_MERGE_OVERLAPPING_LANES')
                require(doc['lanes'][lane]['status']=='PASS' and
                    set(doc['lanes'][lane]['cases'])==set(lanes[lane]['cases']) and
                    all(v=='PASS' for v in doc['lanes'][lane]['cases'].values()),
                    'M20_MERGE_INCOMPLETE_LANE')
                result['lanes'][lane]=doc['lanes'][lane]
                if lane == 'C':
                    for field in ('force_stop','process_gone','cold_relaunch'):
                        result[field] = doc.get(field,'NOT_RUN')
                selected.add(lane)
        result['lanes_requested']=sorted(selected)
        result['overall']=SUCCESS if selected==set(lanes) else 'PASS_SELECTED_M20_LANES'
        require('C' not in selected or any(d.get('force_stop')=='PASS' and
                d.get('process_gone')=='PASS' and d.get('cold_relaunch')=='PASS'
                for d in docs),'M20_MERGE_NO_REAL_PROCESS_EVIDENCE')
    except m14.DeviceGateError as error:
        result.update(overall='FAILED_OR_BLOCKED',failure_code=error.code)
    except Exception:
        result.update(overall='FAILED_OR_BLOCKED',failure_code='M20_MERGE_INVALID_INPUT')
    store(args.output,result)
    return 0 if result['overall'] in (SUCCESS,'PASS_SELECTED_M20_LANES') else 1


def maintenance(args):
    try:
        require(args.transport in ('adb','termux-root'),'M20_TRANSPORT_REQUIRED')
        require(args.inventory or args.cleanup_fixture,'M20_MAINTENANCE_ACTION_REQUIRED')
        if args.cleanup_fixture:
            require(args.maintenance_opt_in,'M20_FIXTURE_CLEANUP_CONSENT_REQUIRED')
            require(re.fullmatch(r'm(?:19|20):[0-9a-f]{24}',args.cleanup_fixture),
                    'M20_FIXTURE_ID_INVALID')
        device=m14.Transport(args.transport)
        case='cleanupVerifiedFixture' if args.cleanup_fixture else 'inspectOwnedInventory'
        args_list=['am','instrument','-w','-r','-e','class',MAINT_CLASS+'#'+case]
        if args.cleanup_fixture:
            args_list+=['-e','m20_maintenance_opt_in','true',
                        '-e','m20_cleanup_id',args.cleanup_fixture]
        raw=device.shell(*args_list,m14.RUNNER,timeout=90)
        summary=m14.parse_instrumentation(raw,frozenset((case,)))
        if args.inventory:
            matches=re.findall(r'INSTRUMENTATION_STATUS: m20_inventory=([^\n]*)',raw)
            require(len(matches)==1 and len(matches[0])<=40000,'M20_INVENTORY_INVALID')
            entries=[e for e in matches[0].split(',') if e]
            require(len(entries)<=1000 and all(re.fullmatch(
                r'[0-9a-f]{24}|m19-unverified:[0-9a-f]{24}',e) for e in entries),
                'M20_INVENTORY_INVALID')
            print(json.dumps({'inventory_opaque_ids':entries,'m19_cleanup_requires_full_validation':True}))
        else:
            require('INSTRUMENTATION_STATUS: m20_cleanup_verified=true' in raw,
                    'M20_CLEANUP_NOT_CONFIRMED')
            print(json.dumps({'cleanup':'PASS','fixture_id':args.cleanup_fixture}))
        return 0
    except m14.DeviceGateError as error:
        print(json.dumps({'maintenance':'FAILED_OR_BLOCKED','failure_code':error.code}))
        return 1


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=ROOT)
    p.add_argument('--run-id',type=int)
    p.add_argument('--transport',choices=('termux-root','adb'))
    selection=p.add_mutually_exclusive_group(required=True)
    selection.add_argument('--all',action='store_true')
    selection.add_argument('--all-safe-lanes',action='store_true')
    selection.add_argument('--lane')
    selection.add_argument('--list-lanes',action='store_true')
    selection.add_argument('--merge-reports',nargs='+')
    selection.add_argument('--inventory',action='store_true')
    selection.add_argument('--cleanup-fixture')
    p.add_argument('--ui-opt-in',action='store_true')
    p.add_argument('--force-stop-opt-in',action='store_true')
    p.add_argument('--test-profile-opt-in',action='store_true')
    p.add_argument('--install',action='store_true')
    p.add_argument('--allow-replace',action='store_true')
    p.add_argument('--maintenance-opt-in',action='store_true')
    p.add_argument('--output',type=Path)
    args=p.parse_args(argv)
    if args.list_lanes:
        print(json.dumps({k:dict(title=v['title'],count=len(v['cases']),requires_force_stop=v['force_stop'])
                          for k,v in matrix().items()},indent=2))
        return 0
    if args.inventory or args.cleanup_fixture: return maintenance(args)
    if args.merge_reports:
        p.error('--merge-reports requires --output') if not args.output else None
        return merge(args)
    if not args.output or not args.run_id or not args.transport:
        p.error('device qualification requires --run-id, --transport and --output')
    return execute(args)

if __name__=='__main__': sys.exit(main())
