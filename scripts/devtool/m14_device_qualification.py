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
    def __init__(self, code):
        self.code = code
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
    require(run.get('head_branch') == 'feature/m14-isolated-device-qualification' or
            run.get('head_branch') == 'master', 'WRONG_CI_BRANCH')
    steps = jobs.get('jobs', [{}])[0].get('steps', [])
    successful = {s.get('name') for s in steps if s.get('conclusion') == 'success'}
    require({'M14 device qualification runner regressions',
             'M14 compile isolated Android instrumentation APK',
             'M14 upload isolated instrumentation APK'} <= successful,
            'M14_CI_STEPS_INCOMPLETE')

def verified_ci_checkout(run, branch_commit):
    """Resolve immutable CI checkout identity without confusing a PR merge with HEAD.

    GitHub `pull_request` builds compile refs/pull/N/merge (GITHUB_SHA), while
    Actions run.head_sha refers to the feature tip. A merge is trusted only if
    its current GitHub ref, PR association, and both Git parents agree.
    If a PR or base moved after CI, fail closed and require a fresh run.
    """
    require(run.get('head_sha') == branch_commit, 'CI_HEAD_MISMATCH')
    if run.get('event') == 'push':
        branch = run.get('head_branch')
        require(branch in ('master', 'feature/m14-isolated-device-qualification'),
                'UNEXPECTED_PUSH_BRANCH')
        return branch_commit, f'refs/heads/{branch}'
    require(run.get('event') == 'pull_request', 'UNEXPECTED_CI_EVENT')
    linked = run.get('pull_requests')
    require(type(linked) is list and len(linked) == 1, 'PR_ASSOCIATION_AMBIGUOUS')
    linked_pr = linked[0]
    number = linked_pr.get('number')
    require(type(number) is int and number > 0, 'INVALID_PR_NUMBER')
    head = linked_pr.get('head') or {}
    base = linked_pr.get('base') or {}
    base_sha = base.get('sha')
    require(head.get('sha') == branch_commit and head.get('ref') == run.get('head_branch') and
            SHA40.fullmatch(base_sha or '') is not None,
            'PR_HEAD_OR_BASE_MISMATCH')
    pr = json_from_gh([f'repos/{REPO}/pulls/{number}'])
    require(pr.get('number') == number and
            (pr.get('head') or {}).get('sha') == branch_commit and
            (pr.get('base') or {}).get('sha') == base_sha and
            (pr.get('head') or {}).get('ref') == run.get('head_branch'),
            'PR_CHANGED_SINCE_CI')
    merge_sha = pr.get('merge_commit_sha')
    require(isinstance(merge_sha, str) and SHA40.fullmatch(merge_sha) is not None,
            'PR_MERGE_COMMIT_UNAVAILABLE')
    ref = json_from_gh([f'repos/{REPO}/git/ref/pull/{number}/merge'])
    require(ref.get('ref') == f'refs/pull/{number}/merge' and
            (ref.get('object') or {}).get('sha') == merge_sha,
            'PR_MERGE_REF_MISMATCH')
    merge = json_from_gh([f'repos/{REPO}/git/commits/{merge_sha}'])
    parents = merge.get('parents') or []
    require(merge.get('sha') == merge_sha and len(parents) == 2 and
            [p.get('sha') for p in parents] == [base_sha, branch_commit],
            'PR_MERGE_PARENTS_MISMATCH')
    return merge_sha, f'refs/pull/{number}/merge'

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
    def instrument(self):
        return self.shell('am','instrument','-w','-r','-e','class',CLASS,RUNNER,timeout=600)
    def launch(self):
        return self.shell('am','start','-W','-n',f'{PACKAGE}/.MainActivity',timeout=40)
    def device_info(self):
        sdk=self.shell('getprop','ro.build.version.sdk',timeout=15).strip()
        abi=self.shell('getprop','ro.product.cpu.abi',timeout=15).strip()
        require(sdk.isdecimal() and 26 <= int(sdk) <= 100 and
                abi in ('arm64-v8a','armeabi-v7a','x86','x86_64'),
                'UNSUPPORTED_ANDROID_DEVICE')
        return {'api_level':int(sdk),'abi':abi}  # no serial, phone ID or path

def parse_instrumentation(output):
    # Delimited AndroidJUnitRunner STATUS records, never persist raw device logs.
    completed=set()
    for m in re.finditer(r'INSTRUMENTATION_STATUS: test=([A-Za-z][A-Za-z0-9_]*)',output):
        tail=output[m.end():]
        status=re.search(r'INSTRUMENTATION_STATUS_CODE:\s*(-?\d+)',tail)
        if status and int(status.group(1)) == 0 and m.group(1) in TESTS:
            completed.add(m.group(1))
    failed=bool(re.search(r'INSTRUMENTATION_STATUS_CODE:\s*-(?:2|1)\b',output))
    code=re.search(r'INSTRUMENTATION_CODE:\s*(-?\d+)',output)
    require(not failed and code is not None and code.group(1)=='-1' and completed==TESTS,
            'INSTRUMENTATION_INCOMPLETE_OR_FAILED')
    return {'status':'PASS','completed':len(completed),'expected':len(TESTS),
            'cases':{name:'PASS' for name in sorted(TESTS)}}

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
            'repository':REPO,'source_commit':None,'ci_checkout_commit':None,'ci_checkout_ref':None,
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
        head=git_head(repo)
        report['source_commit']=head
        require(args.run_id>0,'INVALID_RUN_ID')
        run_data=json_from_gh([f'repos/{REPO}/actions/runs/{args.run_id}'])
        jobs=json_from_gh([f'repos/{REPO}/actions/runs/{args.run_id}/jobs?per_page=100'])
        verify_ci(run_data,jobs,head)
        ci_commit, ci_ref = verified_ci_checkout(run_data, head)
        report['ci']='PASS'
        report['ci_checkout_commit']=ci_commit
        report['ci_checkout_ref']=ci_ref
        with tempfile.TemporaryDirectory(prefix='cinderbox-m14-') as directory:
            temp=Path(directory)
            main=temp/'debug';test=temp/'instrumentation'
            main.mkdir();test.mkdir()
            command(['gh','run','download',str(args.run_id),'--repo',REPO,'--name','debug-apk','--dir',str(main)],timeout=240)
            command(['gh','run','download',str(args.run_id),'--repo',REPO,'--name','m14-androidtest-apk','--dir',str(test)],timeout=240)
            apk,test_apk,digest,test_digest=verify_artifacts(
                main,test,ci_commit,source_ref=ci_ref,run_id=args.run_id)
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
    p.add_argument('--transport',choices=('adb','termux-root'),required=True)
    p.add_argument('--install',action='store_true',help='Explicit consent to install CI debug and test APKs')
    p.add_argument('--allow-replace',action='store_true',help='Explicit consent to replace existing matching-signature app/test APKs')
    p.add_argument('--launch',action='store_true',help='Opt in to launch the normal Activity after tests')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    return run(args)

if __name__=='__main__': sys.exit(main())
