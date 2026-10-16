#!/usr/bin/env python3
"""M19 source-bound interrupted checkpoint recovery across genuine Android process death.

Device effects ONLY with explicit --force-stop-opt-in, --ui-opt-in, --install, and
--allow-replace.  am force-stop stops the app process (and may interrupt its active
services), so use an intentionally signed-out test installation with no active jobs.
NEVER pm clear, uninstall, reboot, grant permissions, access saves, or publish.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import secrets
import sys
import tempfile

import m14_device_qualification as m14
import m17_device_qualification as m17

REPO = m14.REPO
CLASS = 'com.sdvsync.qualification.M19InterruptedRecoveryDeviceTest'
PREPARE = 'seedInterruptedDownloadCheckpoint'
VERIFY = 'verifyInterruptedCheckpointAndReviewAfterColdRelaunch'
TESTS = frozenset((PREPARE, VERIFY))
CI_STEP = 'M19 interrupted download checkpoint recovery regressions'


def require(condition, reason):
    m14.require(condition, reason)


def verify_ci(run, jobs, head):
    m14.verify_ci(run, jobs, head)
    successes = {step.get('name') for job in jobs.get('jobs', [])
                 for step in job.get('steps', []) if step.get('conclusion') == 'success'}
    require(CI_STEP in successes, 'M19_CI_REGRESSIONS_NOT_PASSED')
    require(run.get('head_branch') in ('feature/m19-interrupted-operation-recovery', 'master'),
            'M19_WRONG_CI_BRANCH')


def pid_of(device):
    # pidof has exit 1 when the app is stopped; shell must not treat that as
    # a transport failure. Command string is a constant, no user interpolation.
    result = device.shell('sh', '-c', 'pidof com.sdvsync || true', timeout=15).strip()
    require(result == '' or re.fullmatch(r'[0-9]+(?:\s+[0-9]+)*', result) is not None,
            'M19_PIDOF_UNEXPECTED_OUTPUT')
    return tuple(result.split()) if result else ()


def assert_launch(output):
    require(re.search(r'(?m)^Status:\s*ok\s*$', output) is not None and
            re.search(r'(?m)^Activity:\s*com\.sdvsync/\.MainActivity\s*$', output)
            is not None, 'M19_ACTIVITY_LAUNCH_FAILED')


def instrument_stage(device, method, nonce):
    raw = device.shell('am', 'instrument', '-w', '-r',
                       '-e', 'class', CLASS + '#' + method,
                       '-e', 'm19_nonce', nonce, m14.RUNNER, timeout=600)
    return m14.parse_instrumentation(raw, tests=frozenset((method,)))


def run(args):
    report = {
        'schema_version': 1, 'producer': 'cinderbox-m19-device',
        'scope': 'authorized-isolated-download-checkpoint-interruption-cold-relaunch',
        'repository': REPO, 'github_run_id': args.run_id,
        'source_commit': None, 'runner_source_commit': None,
        'ci_checkout_commit': None, 'ci_checkout_ref': None,
        'ci': 'NOT_RUN', 'apk_sha256': None, 'test_apk_sha256': None,
        'transport': args.transport, 'device': None,
        'install': 'NOT_RUN', 'checkpoint_preparation': 'NOT_RUN',
        'pre_stop_launch': 'NOT_RUN', 'force_stop': 'NOT_RUN',
        'process_gone': 'NOT_RUN', 'cold_relaunch': 'NOT_RUN',
        'checkpoint_recovery': 'NOT_RUN', 'fixture_cleanup': 'NOT_CONFIRMED',
        'instrumentation': 'NOT_RUN', 'overall': 'INCOMPLETE', 'failure_code': None,
        'force_stop_opt_in': False, 'live_ui_opt_in': False,
        'm14_reexecuted': False, 'm15_reexecuted': False, 'm17_reexecuted': False, 'm18_reexecuted': False,
        'device_qualified': False, 'release_qualified': False, 'publication_allowed': False,
        'automatic_device_install': False, 'automatic_uninstall': False,
        'automatic_data_clear': False, 'automatic_reboot': False,
    }
    try:
        require(args.force_stop_opt_in, 'FORCE_STOP_REQUIRES_EXPLICIT_FLAG')
        report['force_stop_opt_in'] = True
        require(args.ui_opt_in, 'LIVE_UI_REQUIRES_EXPLICIT_FLAG')
        report['live_ui_opt_in'] = True
        require(args.install and args.allow_replace,
                'INSTALL_AND_REPLACE_REQUIRE_EXPLICIT_FLAGS')
        require(args.test_profile_opt_in, 'ISOLATED_TEST_PROFILE_REQUIRES_EXPLICIT_FLAG')
        repo = args.repo.resolve()
        local_head = m14.git_head(repo)
        tracked = ('scripts/devtool/m14_device_qualification.py',
                   'scripts/devtool/m19_device_qualification.py',
                   'app/src/androidTest/java/com/sdvsync/qualification/M19InterruptedRecoveryDeviceTest.kt')
        dirty = m14.command(['git','-C',str(repo),'status','--porcelain','--',*tracked]).strip()
        require(not dirty, 'LOCAL_QUALIFIER_MODIFIED')
        head = args.ci_head or local_head
        require(m14.SHA40.fullmatch(head or '') is not None, 'INVALID_CI_HEAD')
        require(args.run_id > 0, 'INVALID_RUN_ID')
        report['runner_source_commit'] = local_head
        report['source_commit'] = head
        run_data = m14.json_from_gh([f'repos/{REPO}/actions/runs/{args.run_id}'])
        jobs = m14.json_from_gh([f'repos/{REPO}/actions/runs/{args.run_id}/jobs?per_page=100'])
        verify_ci(run_data, jobs, head)
        with tempfile.TemporaryDirectory(prefix='cinderbox-m19-') as directory:
            temp = Path(directory)
            main, tests = temp/'debug', temp/'instrumentation'
            main.mkdir(); tests.mkdir()
            m14.command(['gh','run','download',str(args.run_id),'--repo',REPO,
                         '--name','debug-apk','--dir',str(main)],timeout=240)
            m14.command(['gh','run','download',str(args.run_id),'--repo',REPO,
                         '--name','m14-androidtest-apk','--dir',str(tests)],timeout=240)
            provenance=m14.read_json(main/'M3_PROVENANCE.json')
            commit,ref=m14.verified_ci_checkout(run_data,head,
                artifact_commit=provenance.get('source_commit'),
                artifact_ref=provenance.get('source_ref'))
            apk,test_apk,digest,test_digest=m14.verify_artifacts(
                main,tests,commit,source_ref=ref,run_id=args.run_id)
            report.update(ci='PASS',ci_checkout_commit=commit,ci_checkout_ref=ref,
                          apk_sha256=digest,test_apk_sha256=test_digest)
            device=m14.Transport(args.transport)
            report['device']=device.device_info()
            app_installed=device.installed(m14.PACKAGE)
            test_installed=device.installed(m14.TEST_PACKAGE)
            report['install']='ATTEMPTED'
            result=device.install(apk,replace=app_installed)
            require('Success' in result.splitlines(),'M19_APP_INSTALL_FAILED')
            require(device.installed(m14.PACKAGE),'M19_APP_INSTALL_NOT_CONFIRMED')
            result=device.install(test_apk,replace=test_installed,test=True)
            require('Success' in result.splitlines(),'M19_TEST_INSTALL_FAILED')
            require(device.installed(m14.TEST_PACKAGE),'M19_TEST_INSTALL_NOT_CONFIRMED')
            report['install']='PASS'
            nonce=secrets.token_hex(16)  # never persisted in reports
            report['checkpoint_preparation']='ATTEMPTED'
            pre=instrument_stage(device,PREPARE,nonce)
            require(pre['status']=='PASS','M19_PREPARE_INSTRUMENTATION_FAILED')
            report['checkpoint_preparation']='PASS'
            report['pre_stop_launch']='ATTEMPTED'
            assert_launch(device.launch())
            require(bool(pid_of(device)),'M19_PROCESS_NOT_ALIVE_BEFORE_STOP')
            report['pre_stop_launch']='PASS'
            report['force_stop']='ATTEMPTED'
            device.shell('am','force-stop',m14.PACKAGE,timeout=30)
            report['force_stop']='PASS'
            require(not pid_of(device),'M19_PROCESS_SURVIVED_FORCE_STOP')
            report['process_gone']='PASS'
            report['cold_relaunch']='ATTEMPTED'
            assert_launch(device.launch())
            require(bool(pid_of(device)),'M19_PROCESS_NOT_RESTARTED')
            report['cold_relaunch']='PASS'
            report['checkpoint_recovery']='ATTEMPTED'
            post=instrument_stage(device,VERIFY,nonce)
            require(post['status']=='PASS','M19_POST_RECOVERY_INSTRUMENTATION_FAILED')
            report['checkpoint_recovery']='PASS'
            report['fixture_cleanup']='PASS'
            report['instrumentation']={'status':'PASS','completed':2,'expected':2,
                 'cases':{PREPARE:'PASS',VERIFY:'PASS'},'final_code':-1}
            report['overall']='PASS_INTERRUPTED_OPERATION_RECOVERY_AUTOMATION'
    except m14.DeviceGateError as error:
        report['failure_code']=error.code
        report['overall']='FAILED_OR_BLOCKED'
        if error.case_summary is not None:
            report['instrumentation']=error.case_summary
    except Exception:
        report['failure_code']='UNEXPECTED_FAILURE'
        report['overall']='FAILED_OR_BLOCKED'
    m14.write_report(args.output,report)
    print(json.dumps({'overall':report['overall'],'failure_code':report['failure_code'],
                      'report':str(args.output)},sort_keys=True))
    return 0 if report['overall']=='PASS_INTERRUPTED_OPERATION_RECOVERY_AUTOMATION' else 1


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--run-id',type=int,required=True)
    p.add_argument('--ci-head',default=None)
    p.add_argument('--transport',choices=('adb','termux-root'),required=True)
    p.add_argument('--ui-opt-in',action='store_true')
    p.add_argument('--force-stop-opt-in',action='store_true')
    p.add_argument('--test-profile-opt-in',action='store_true',
                   help='Confirm intentionally signed-out test installation with no active jobs')
    p.add_argument('--install',action='store_true')
    p.add_argument('--allow-replace',action='store_true')
    p.add_argument('--output',type=Path,required=True)
    return run(p.parse_args(argv))

if __name__=='__main__': sys.exit(main())
