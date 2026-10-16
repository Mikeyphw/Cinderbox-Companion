#!/usr/bin/env python3
"""M14 explicit Android device tests, rooted Termux or one ADB device.

Debug-only, no uninstall, no data clear, no implicit app replacement, and no
modification of genuine game, save or Steam paths. Tests use isolated cache fixtures.
Download provenance is a CI self-report, not a production release attestation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import zipfile

REPO = 'Mikeyphw/Cinderbox-Companion'
PACKAGE = 'com.sdvsync'
TEST_PACKAGE = 'com.sdvsync.test'
CLASS = 'com.sdvsync.qualification.M14IsolatedDeviceTest'
RUNNER = f'{TEST_PACKAGE}/androidx.test.runner.AndroidJUnitRunner'
TESTS = frozenset((
    'checkpointResumeAndDiscard', 'crashStyleModProfileRollback',
    'modBatchFailureRollsBackMultipleChanges',
    'corruptModJournalCannotAffectDownloadCheckpoint',
    'saveRestorePreservesOtherFiles', 'corruptSaveJournalPreservesLiveSave',
    'operationCenterSimultaneousFailuresAreReadOnly',
    'capacityCheckNeverGuessesUnknownDownloadSize',
))
SHA40 = re.compile('[0-9a-f]{40}\\Z')
SHA64 = re.compile('[0-9a-f]{64}\\Z')

class DeviceGateError(Exception):
    def __init__(self, code, *, case_summary=None):
        self.code = code
        self.case_summary = case_summary
        super().__init__(code)

def require(condition, code):
    if not condition:
        raise DeviceGateError(code)

def command(args, timeout=90):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise DeviceGateError('COMMAND_UNAVAILABLE_OR_TIMEOUT') from None
    if p.returncode:
        raise DeviceGateError('COMMAND_FAILED')
    return p.stdout

def json_from_gh(args):
    raw = command(['gh', 'api', *args], timeout=45)
    try:
        data = json.loads(raw)
    except ValueError:
        raise DeviceGateError('INVALID_GITHUB_RESPONSE') from None
    require(type(data) is dict, 'INVALID_GITHUB_RESPONSE')
    return data

def list_from_gh(args):
    """Read a GitHub list endpoint without accepting objects or malformed responses."""
    raw = command(['gh', 'api', *args], timeout=45)
    try:
        data = json.loads(raw)
    except ValueError:
        raise DeviceGateError('INVALID_GITHUB_RESPONSE') from None
    require(type(data) is list and len(data) <= 100, 'INVALID_GITHUB_RESPONSE')
    return data

def git_head(repo):
    commit = command(['git','-C',str(repo),'rev-parse','HEAD']).strip()
    require(SHA40.fullmatch(commit) is not None, 'INVALID_LOCAL_COMMIT')
    remote = command(['git','-C',str(repo),'remote','get-url','origin']).strip()
    require('Mikeyphw/Cinderbox-Companion' in remote, 'WRONG_REPOSITORY')
    return commit

def verify_ci(run, jobs, commit):
    # Reuse M13's complete legacy CI step audit; it rejects skipped tests.
    from m13_qualification import assess_ci
    try:
        assess_ci(run, jobs, commit)
    except Exception:
        raise DeviceGateError('CI_QUALIFICATION_FAILED') from None
    require(run.get('head_branch') in (
        'feature/m14-isolated-device-qualification',
        'feature/m14-postmerge-device-provenance',
        'feature/m15-integrated-android-qualification',
        'feature/m17-android-ui-lifecycle',
        'feature/m18-process-death-recovery',
        'feature/m19-interrupted-operation-recovery',
            'feature/m20-consolidated-resilience', 'master'), 'WRONG_CI_BRANCH')
    steps = jobs.get('jobs', [{}])[0].get('steps', [])
    successful = {s.get('name') for s in steps if s.get('conclusion') == 'success'}
    require({'M14 device qualification runner regressions',
             'M14 compile isolated Android instrumentation APK',
             'M14 upload isolated instrumentation APK'} <= successful,
            'M14_CI_STEPS_INCOMPLETE')

def verified_ci_checkout(run, branch_commit, *, artifact_commit=None, artifact_ref=None):
    """Bind CI build provenance to the source GitHub actually checked out.

    The Actions API reports the feature SHA for pull_request runs, even when
    checkout built a synthetic PR merge commit. After a PR is merged, its run's
    pull_requests may be empty and refs/pull/N/merge may be removed. Recover
    association from GitHub's commit -> PR endpoint and verify the immutable
    checkout commit's exact parent SHAs. Never treat master merge SHA as the
    historical PR test build, and never bypass M3/M13 evidence verification.
    """
    require(run.get('head_sha') == branch_commit and
            SHA40.fullmatch(branch_commit or '') is not None, 'CI_HEAD_MISMATCH')
    if run.get('event') == 'push':
        branch = run.get('head_branch')
        require(branch in ('master', 'feature/m14-isolated-device-qualification'),
                'UNEXPECTED_PUSH_BRANCH')
        expected_ref = f'refs/heads/{branch}'
        require(artifact_commit in (None, branch_commit) and
                artifact_ref in (None, expected_ref), 'PUSH_ARTIFACT_IDENTITY_MISMATCH')
        return branch_commit, expected_ref
    require(run.get('event') == 'pull_request', 'UNEXPECTED_CI_EVENT')
    branch_name = run.get('head_branch')
    require(branch_name in ('feature/m14-isolated-device-qualification',
                            'feature/m14-postmerge-device-provenance',
                            'feature/m15-integrated-android-qualification',
                            'feature/m17-android-ui-lifecycle',
                            'feature/m18-process-death-recovery',
                            'feature/m19-interrupted-operation-recovery',
                            'feature/m20-consolidated-resilience'),
            'UNEXPECTED_PR_BRANCH')
    linked = run.get('pull_requests')
    require(type(linked) is list, 'PR_ASSOCIATION_AMBIGUOUS')
    if not linked:
        # GitHub removes the run -> PR association for some merged PRs.
        # Commit association is explicit and still available after merging.
        linked = list_from_gh([f'repos/{REPO}/commits/{branch_commit}/pulls?per_page=100'])
    matching = [x for x in linked if type(x) is dict and
                (x.get('head') or {}).get('sha') == branch_commit and
                (x.get('head') or {}).get('ref') == branch_name and
                type(x.get('number')) is int and x['number'] > 0]
    require(len(matching) == 1 and len(linked) == 1, 'PR_ASSOCIATION_AMBIGUOUS')
    association = matching[0]
    number = association['number']
    base_sha = (association.get('base') or {}).get('sha')
    require(isinstance(base_sha, str) and SHA40.fullmatch(base_sha) is not None,
            'PR_HEAD_OR_BASE_MISMATCH')
    pr = json_from_gh([f'repos/{REPO}/pulls/{number}'])
    require(pr.get('number') == number and
            (pr.get('head') or {}).get('sha') == branch_commit and
            (pr.get('head') or {}).get('ref') == branch_name and
            (pr.get('base') or {}).get('sha') == base_sha,
            'PR_CHANGED_SINCE_CI')
    expected_ref = f'refs/pull/{number}/merge'
    if artifact_ref is not None:
        require(artifact_ref == expected_ref, 'PR_ARTIFACT_REF_MISMATCH')
    merged = pr.get('state') == 'closed' and bool(pr.get('merged_at'))
    if merged:
        # A merged PR's merge_commit_sha is the FINAL master merge/squash,
        # not the ephemeral merge commit that Actions built earlier.
        require(bool(association.get('merged_at')), 'PR_ASSOCIATION_AMBIGUOUS')
        from datetime import datetime, timezone
        try:
            run_started = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
            merged_at = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
        except (KeyError, AttributeError, ValueError):
            raise DeviceGateError('PR_TIMELINE_UNVERIFIABLE') from None
        require(run_started <= merged_at and
                (association.get('merged_at') == pr.get('merged_at')),
                'PR_TIMELINE_UNVERIFIABLE')
        require(isinstance(artifact_commit, str) and
                SHA40.fullmatch(artifact_commit) is not None and
                artifact_ref == expected_ref,
                'MERGED_PR_REQUIRES_ARTIFACT_SOURCE')
        merge_sha = artifact_commit
    else:
        require(pr.get('state') == 'open', 'PR_STATE_UNVERIFIABLE')
        merge_sha = pr.get('merge_commit_sha')
        require(isinstance(merge_sha, str) and SHA40.fullmatch(merge_sha) is not None,
                'PR_MERGE_COMMIT_UNAVAILABLE')
        if artifact_commit is not None:
            require(artifact_commit == merge_sha, 'PR_ARTIFACT_COMMIT_MISMATCH')
        ref = json_from_gh([f'repos/{REPO}/git/ref/pull/{number}/merge'])
        require(ref.get('ref') == expected_ref and
                (ref.get('object') or {}).get('sha') == merge_sha,
                'PR_MERGE_REF_MISMATCH')
    commit = json_from_gh([f'repos/{REPO}/git/commits/{merge_sha}'])
    parents = commit.get('parents') or []
    require(commit.get('sha') == merge_sha and len(parents) == 2 and
            [x.get('sha') for x in parents] == [base_sha, branch_commit],
            'PR_MERGE_PARENTS_MISMATCH')
    return merge_sha, expected_ref

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):
            h.update(data)
    return h.hexdigest()

def read_json(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size < 2_000_000,
            'INVALID_EVIDENCE_FILE')
    try:
        result=json.loads(path.read_text(encoding='utf-8'))
    except (UnicodeError, ValueError):
        raise DeviceGateError('INVALID_EVIDENCE_FILE') from None
    require(type(result) is dict,'INVALID_EVIDENCE_FILE')
    return result

def validate_apk(apk, *, expected_digest=None):
    require(apk.is_file() and not apk.is_symlink() and 4096 <= apk.stat().st_size <= 256*1024*1024,
            'INVALID_APK_FILE')
    try:
        with zipfile.ZipFile(apk) as z:
            names=z.namelist()
            require(len(names)==len(set(names)) and {'AndroidManifest.xml','classes.dex'} <= set(names),
                    'INVALID_APK_STRUCTURE')
            require(z.testzip() is None, 'INVALID_APK_STRUCTURE')
    except (zipfile.BadZipFile, OSError):
        raise DeviceGateError('INVALID_APK_STRUCTURE') from None
    digest=sha256(apk)
    if expected_digest is not None:
        require(digest == expected_digest, 'APK_DIGEST_MISMATCH')
    return digest

def verify_artifacts(main_dir, test_dir, commit, *, source_ref=None, run_id=None):
    prov=read_json(main_dir/'M3_PROVENANCE.json')
    qual=read_json(main_dir/'M13_QUALIFICATION.json')
    require(prov.get('repository') == REPO and prov.get('source_commit') == commit and
            prov.get('variant')=='debug' and prov.get('format')=='apk' and
            prov.get('qualified_release') is False and prov.get('publication_allowed') is False,
            'M3_SOURCE_MISMATCH')
    if source_ref is not None:
        require(prov.get('source_ref') == source_ref, 'M3_REF_MISMATCH')
    if run_id is not None:
        require(prov.get('github_run_id') == str(run_id), 'M3_RUN_MISMATCH')
    info=prov.get('apk', {})
    require(type(info) is dict and SHA64.fullmatch(info.get('sha256','')) is not None and
            info.get('package_name') == PACKAGE and info.get('debug_signed') is True and
            info.get('signature_verified') is True,
            'M3_APK_IDENTITY_MISMATCH')
    apks=list(main_dir.glob('*.apk'))
    require(len(apks)==1 and apks[0].name == info.get('filename') and
            apks[0].stat().st_size == info.get('size_bytes'), 'M3_APK_IDENTITY_MISMATCH')
    digest=validate_apk(apks[0],expected_digest=info['sha256'])
    require(qual.get('producer')=='cinderbox-m13' and qual.get('source_commit')==commit and
            qual.get('source_contract')=='PASS' and
            qual.get('apk_integrity')=='PASS_SHA256_MATCHES_M3' and
            qual.get('artifact_sha256') == digest and
            qual.get('release_qualified') is False and
            qual.get('publication_allowed') is False, 'M13_EVIDENCE_MISMATCH')
    tests=list(test_dir.glob('*.apk'))
    require(len(tests)==1, 'M14_TEST_APK_MISSING')
    test_digest=validate_apk(tests[0])
    return apks[0], tests[0], digest, test_digest

class Transport:
    def __init__(self, kind):
        require(kind in ('adb','termux-root'), 'UNKNOWN_TRANSPORT')
        self.kind=kind
        self.serial=None
        if kind == 'adb':
            output=command(['adb','devices'])
            devices=[p[0] for l in output.splitlines()[1:]
                     if len(p:=l.split())==2 and p[1]=='device']
            require(len(devices)==1, 'REQUIRE_EXACTLY_ONE_ADB_DEVICE')
            self.serial=devices[0]
        else:
            # Only used when explicitly selected; no implicit privilege escalation.
            require(command(['su','-c','id -u'],timeout=15).strip() == '0',
                    'ROOT_TRANSPORT_NOT_AUTHORIZED')
    def shell(self,*args,timeout=120):
        if self.kind=='adb':
            return command(['adb','-s',self.serial,'shell',*args],timeout=timeout)
        return command(['su','-c',shlex.join(args)],timeout=timeout)
    def installed(self, package):
        # list packages exits successfully even for an absent package. A PM
        # permission failure must BLOCK installation, not be mistaken for absence.
        v=self.shell('pm','list','packages',package,timeout=15)
        return any(line.strip() == 'package:'+package for line in v.splitlines())
    def install(self, apk, *, replace=False, test=False):
        flags=['-r'] if replace else []
        if test: flags+=['-t']
        if self.kind=='adb':
            return command(['adb','-s',self.serial,'install',*flags,str(apk)],timeout=240)
        return self.shell('pm','install',*flags,str(apk),timeout=240)
    def instrument(self, *, test_class=CLASS):
        return self.shell('am','instrument','-w','-r','-e','class',test_class,RUNNER,timeout=600)
    def launch(self):
        return self.shell('am','start','-W','-n',f'{PACKAGE}/.MainActivity',timeout=40)
    def device_info(self):
        sdk=self.shell('getprop','ro.build.version.sdk',timeout=15).strip()
        abi=self.shell('getprop','ro.product.cpu.abi',timeout=15).strip()
        require(sdk.isdecimal() and 26 <= int(sdk) <= 100 and
                abi in ('arm64-v8a','armeabi-v7a','x86','x86_64'),
                'UNSUPPORTED_ANDROID_DEVICE')
        return {'api_level':int(sdk),'abi':abi}  # no serial, phone ID or path

def parse_instrumentation(output, tests=TESTS):
    """Parse AndroidJUnitRunner status blocks without saving raw device output."""
    cases = {name: 'NOT_COMPLETED' for name in sorted(tests)}
    current = None
    failed_event = False
    for line in output.splitlines():
        match = re.match(r'INSTRUMENTATION_STATUS: test=([A-Za-z][A-Za-z0-9_]*)\s*$', line)
        if match:
            current = match.group(1)
            continue
        match = re.match(r'INSTRUMENTATION_STATUS_CODE:\s*(-?\d+)\s*$', line)
        if match:
            status = int(match.group(1))
            if status in (-1, -2):
                failed_event = True
            if current in cases and status in (0, -1, -2):
                cases[current] = {0: 'PASS', -1: 'ERROR', -2: 'FAIL'}[status]
            current = None
    final_codes = re.findall(r'(?m)^INSTRUMENTATION_CODE:\s*(-?\d+)\s*$', output)
    final_code = int(final_codes[-1]) if final_codes else None
    complete = sum(value == 'PASS' for value in cases.values())
    accepted = (not failed_event and final_code == -1 and
                complete == len(tests) and len(final_codes) == 1)
    summary = {'status': 'PASS' if accepted else 'FAILED_OR_BLOCKED',
               'completed': complete, 'expected': len(tests),
               'cases': cases, 'final_code': final_code}
    if not accepted:
        raise DeviceGateError('INSTRUMENTATION_INCOMPLETE_OR_FAILED', case_summary=summary)
    return summary

def write_report(path, doc):
    path.parent.mkdir(parents=True,exist_ok=True)
    require(not path.is_symlink(),'UNSAFE_REPORT_DESTINATION')
    fd,name=tempfile.mkstemp(prefix='.m14-',suffix='.tmp',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf8') as f:
            json.dump(doc,f,sort_keys=True,indent=2)
            f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)

def run(args):
    report={'schema_version':1,'producer':'cinderbox-m14-device',
            'scope':'explicit-debug-real-device-isolated-fixtures',
            'repository':REPO,'source_commit':None,'runner_source_commit':None,
            'ci_checkout_commit':None,'ci_checkout_ref':None,
            'github_run_id':args.run_id,
            'ci':'NOT_RUN','apk_sha256':None,'test_apk_sha256':None,
            'transport':args.transport,'device':None,'install':'NOT_RUN',
            'instrumentation':'NOT_RUN','launch':'NOT_RUN',
            'overall':'INCOMPLETE','failure_code':None,
            'release_qualified':False,'device_qualified':False,
            'publication_allowed':False,'automatic_device_install':False}
    try:
        require(args.install,'INSTALL_REQUIRES_EXPLICIT_FLAG')
        repo=args.repo.resolve()
        local_head=git_head(repo)
        head=args.ci_head or local_head
        require(SHA40.fullmatch(head or '') is not None, 'INVALID_CI_HEAD')
        report['runner_source_commit']=local_head
        report['source_commit']=head
        require(args.run_id>0,'INVALID_RUN_ID')
        run_data=json_from_gh([f'repos/{REPO}/actions/runs/{args.run_id}'])
        jobs=json_from_gh([f'repos/{REPO}/actions/runs/{args.run_id}/jobs?per_page=100'])
        verify_ci(run_data,jobs,head)
        with tempfile.TemporaryDirectory(prefix='cinderbox-m14-') as directory:
            temp=Path(directory)
            main=temp/'debug';test=temp/'instrumentation'
            main.mkdir();test.mkdir()
            command(['gh','run','download',str(args.run_id),'--repo',REPO,'--name','debug-apk','--dir',str(main)],timeout=240)
            command(['gh','run','download',str(args.run_id),'--repo',REPO,'--name','m14-androidtest-apk','--dir',str(test)],timeout=240)
            provenance=read_json(main/'M3_PROVENANCE.json')
            ci_commit, ci_ref = verified_ci_checkout(
                run_data,head,artifact_commit=provenance.get('source_commit'),
                artifact_ref=provenance.get('source_ref'))
            apk,test_apk,digest,test_digest=verify_artifacts(
                main,test,ci_commit,source_ref=ci_ref,run_id=args.run_id)
            report['ci']='PASS'
            report['ci_checkout_commit']=ci_commit
            report['ci_checkout_ref']=ci_ref
            report['apk_sha256']=digest
            report['test_apk_sha256']=test_digest
            device=Transport(args.transport)
            report['device']=device.device_info()
            app_installed=device.installed(PACKAGE)
            test_installed=device.installed(TEST_PACKAGE)
            require((not app_installed and not test_installed) or args.allow_replace,
                    'EXISTING_INSTALL_REQUIRES_ALLOW_REPLACE')
            report['install']='ATTEMPTED'
            app_install_result=device.install(apk,replace=app_installed)
            require('Success' in app_install_result.splitlines(), 'APP_PACKAGE_INSTALL_FAILED')
            require(device.installed(PACKAGE),'APP_INSTALL_NOT_CONFIRMED')
            report['install']='APP_INSTALLED_TEST_PENDING'
            test_install_result=device.install(test_apk,replace=test_installed,test=True)
            require('Success' in test_install_result.splitlines(), 'TEST_PACKAGE_INSTALL_FAILED')
            require(device.installed(TEST_PACKAGE),'TEST_INSTALL_NOT_CONFIRMED')
            report['install']='PASS'
            report['instrumentation']='ATTEMPTED'
            report['instrumentation']=parse_instrumentation(device.instrument())
            if args.launch:
                # Activity launch acceptance only; does not assert successful login or UI flows.
                out=device.launch()
                require('Error:' not in out and 'Exception' not in out, 'ACTIVITY_LAUNCH_FAILED')
                report['launch']='PASS_ACTIVITY_START_ACCEPTED'
            report['overall']='PASS_ISOLATED_DEVICE_AUTOMATION'
    except DeviceGateError as error:
        report['failure_code']=error.code
        if error.case_summary is not None:
            report['instrumentation']=error.case_summary
        report['overall']='FAILED_OR_BLOCKED'
    except Exception:
        report['failure_code']='UNEXPECTED_FAILURE'
        report['overall']='FAILED_OR_BLOCKED'
    write_report(args.output,report)
    print(json.dumps({'overall':report['overall'],'failure_code':report['failure_code'],
                      'report':str(args.output)},sort_keys=True))
    return 0 if report['overall']=='PASS_ISOLATED_DEVICE_AUTOMATION' else 1

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--run-id',type=int,required=True)
    p.add_argument('--ci-head',default=None,help='Explicit historic feature commit when running after a PR was merged; verified against GitHub CI and PR records')
    p.add_argument('--transport',choices=('adb','termux-root'),required=True)
    p.add_argument('--install',action='store_true',help='Explicit consent to install CI debug and test APKs')
    p.add_argument('--allow-replace',action='store_true',help='Explicit consent to replace existing matching-signature app/test APKs')
    p.add_argument('--launch',action='store_true',help='Opt in to launch the normal Activity after tests')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    return run(args)

if __name__=='__main__': sys.exit(main())
