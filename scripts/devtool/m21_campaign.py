#!/usr/bin/env python3
"""M21: one CI build, separate real workflow/auth/install/release acceptance receipts.

Never sign into Steam, request credentials, modify cloud/saves/game, auto-publish,
uninstall, clear data or silently certify a CI debug APK as a release candidate.
The authenticated and release-candidate lanes are deliberately opt-in.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile

import m14_device_qualification as m14
import m3_apk_signing as signing

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPO = m14.REPO
BRANCH = 'feature/m21-feature-release-readiness'
CI_STEP = 'M21 feature and release readiness source regressions'
SUCCESS = 'PASS_M21_PREPUBLICATION_ACCEPTANCE'


def require(condition, code):
    m14.require(condition, code)


def matrix():
    obj = json.loads((HERE/'m21_scenarios.json').read_text())
    lanes = obj['lanes']
    require(set(lanes) == set('UTIR'), 'M21_LANES_INVALID')
    require([len(lanes[k]['cases']) for k in 'UTIR'] == [4,4,6,4], 'M21_CASE_COUNT_INVALID')
    names = [n for x in lanes.values() for n in x['cases']]
    require(len(names) == len(set(names)) == 18, 'M21_DUPLICATE_OR_MISSING_CASE')
    return lanes


def source_identity(repo):
    tracked = ('scripts/devtool/m14_device_qualification.py', 'scripts/devtool/m21_campaign.py',
               'scripts/devtool/m21_scenarios.json',
               'app/src/androidTest/java/com/sdvsync/qualification/M21ReadinessDeviceTest.kt',
               'app/src/main/java/com/sdvsync/steam/SteamCloudService.kt')
    require(not m14.command(['git','-C',str(repo),'status','--porcelain','--',*tracked]).strip(),
            'M21_QUALIFICATION_SOURCE_DIRTY')
    return m14.git_head(repo)


def verify_ci(run, jobs, head):
    m14.verify_ci(run, jobs, head)
    require(run.get('head_branch') in (BRANCH, 'master'), 'M21_BRANCH_MISMATCH')
    successes = {step.get('name') for job in jobs.get('jobs', [])
                 for step in job.get('steps', []) if step.get('conclusion') == 'success'}
    require(CI_STEP in successes, 'M21_CI_GATE_NOT_PASSED')


def info_report(run_id, transport, chosen):
    return dict(schema_version=1, producer='cinderbox-m21-readiness',
                repository=REPO, github_run_id=run_id,
                source_commit=None, runner_source_commit=None,
                ci_checkout_commit=None, ci_checkout_ref=None, ci='NOT_RUN',
                apk_sha256=None, test_apk_sha256=None, install='NOT_RUN',
                transport=transport, device=None, lanes_requested=chosen,
                lanes={k:dict(status='NOT_RUN', cases={n:'NOT_RUN' for n in v['cases']})
                       for k,v in matrix().items()},
                failure_diagnostics={}, failure_code=None, overall='INCOMPLETE',
                authenticated_verified=False, release_candidate_verified=False,
                release_qualified=False, publication_allowed=False, device_qualified=False,
                historical_74_tests_reexecuted=False,
                automatic_uninstall=False, automatic_data_clear=False, automatic_reboot=False,
                automatic_sign_in=False, automatic_steam_mutation=False,
                automatic_release_publication=False)


def store(path, result):
    m14.write_report(path, result)
    print(json.dumps({'overall':result['overall'],'failure_code':result['failure_code'],
                      'report':str(path)}, sort_keys=True))


def attest_ci(args, report, temp):
    repo = args.repo.resolve()
    head = source_identity(repo)
    report.update(source_commit=head,runner_source_commit=head)
    require(args.run_id and args.run_id > 0,'M21_RUN_ID_REQUIRED')
    run = m14.json_from_gh([f'repos/{REPO}/actions/runs/{args.run_id}'])
    jobs = m14.json_from_gh([f'repos/{REPO}/actions/runs/{args.run_id}/jobs?per_page=100'])
    verify_ci(run,jobs,head)
    main,temp_tests = temp/'debug',temp/'instrumentation'
    main.mkdir();temp_tests.mkdir()
    m14.command(['gh','run','download',str(args.run_id),'--repo',REPO,
                 '--name','debug-apk','--dir',str(main)],timeout=240)
    m14.command(['gh','run','download',str(args.run_id),'--repo',REPO,
                 '--name','m14-androidtest-apk','--dir',str(temp_tests)],timeout=240)
    provenance=m14.read_json(main/'M3_PROVENANCE.json')
    commit,ref = m14.verified_ci_checkout(run,head,
        artifact_commit=provenance.get('source_commit'),artifact_ref=provenance.get('source_ref'))
    apk,test_apk,digest,test_digest = m14.verify_artifacts(
        main,temp_tests,commit,source_ref=ref,run_id=args.run_id)
    report.update(ci='PASS',ci_checkout_commit=commit,ci_checkout_ref=ref,
                  apk_sha256=digest,test_apk_sha256=test_digest)
    return apk,test_apk


def classify(raw,case):
    # Only fixed category names. Raw instrumentation, messages, paths and tokens
    # must never appear in published acceptance receipts.
    parts=[]
    for line in raw.splitlines():
        if line.startswith('INSTRUMENTATION_STATUS_CODE:'):
            block='\n'.join(parts)
            if f'INSTRUMENTATION_STATUS: test={case}' in block:
                return {'category':'ASSERTION_OR_DEVICE_REJECTION' if
                        'AssertionError' in block else 'ANDROID_TEST_EXCEPTION'}
            parts=[]
        else:
            parts.append(line)
    return {'category':'INSTRUMENTATION_INCOMPLETE'}


def instrument(device,klass,case,nonce,authenticated=False):
    flags=['-e','class',klass+'#'+case,'-e','m21_nonce',nonce]
    if authenticated: flags+=['-e','m21_auth_opt_in','true']
    raw=device.shell('am','instrument','-w','-r',*flags,m14.RUNNER,timeout=180)
    try:
        return m14.parse_instrumentation(raw,frozenset((case,)))
    except m14.DeviceGateError as error:
        error.m21_diagnostic={case:classify(raw,case)}
        raise


def run_device(args):
    selected=list(dict.fromkeys(x.strip().upper() for x in args.lane.split(',')))
    report=info_report(args.run_id,args.transport,selected)
    try:
        require(selected and set(selected) <= set('UTI'), 'M21_DEVICE_LANES_INVALID')
        require(args.ui_opt_in and args.install and args.allow_replace,
                'M21_INSTALL_AND_UI_CONSENT_REQUIRED')
        if 'U' in selected:
            require(args.signed_out_opt_in,'M21_OFFLINE_PROFILE_CONSENT_REQUIRED')
        if 'T' in selected:
            require(args.authenticated_opt_in,'M21_AUTHENTICATED_READ_ONLY_CONSENT_REQUIRED')
        if 'I' in selected:
            require(args.installation_check_opt_in and args.upgrade_opt_in,
                    'M21_INSTALLATION_AND_UPGRADE_CONSENT_REQUIRED')
        with tempfile.TemporaryDirectory(prefix='cinderbox-m21-') as directory:
            apk,test_apk=attest_ci(args,report,Path(directory))
            device=m14.Transport(args.transport)
            report['device']=device.device_info()
            report['install']='ATTEMPTED'
            app_installed=device.installed(m14.PACKAGE)
            test_installed=device.installed(m14.TEST_PACKAGE)
            require('Success' in device.install(apk,replace=app_installed).splitlines(),
                    'M21_APPLICATION_INSTALL_FAILED')
            require('Success' in device.install(test_apk,replace=test_installed,test=True).splitlines(),
                    'M21_INSTRUMENTATION_INSTALL_FAILED')
            require(device.installed(m14.PACKAGE) and device.installed(m14.TEST_PACKAGE),
                    'M21_INSTALL_NOT_CONFIRMED')
            report['install']='PASS'
            nonce=secrets.token_hex(16)
            for lane in selected:
                spec=matrix()[lane]
                report['lanes'][lane]['status']='RUNNING'
                order=list(spec['cases'])
                if lane=='I':
                    # Verify package identity BEFORE writing test marker, then
                    # replace the same-signer debug build and confirm persistence.
                    order=['i01MissingGameNotAcceptedAsInstalled',
                           'i02PartialGameFilesNeverMarkedUsable',
                           'i03SyntheticCoreStructureDetectedNotHashVerified',
                           'i06InstalledCinderboxPackageRecognized',
                           'i04SeedOwnedUpgradeMarker',
                           'i05VerifyUpgradePreservesPrivateStateAndCleanup']
                for case in order:
                    if case=='i05VerifyUpgradePreservesPrivateStateAndCleanup':
                        require('Success' in device.install(apk,replace=True).splitlines(),
                                'M21_EXPLICIT_IN_PLACE_UPGRADE_FAILED')
                        require(device.installed(m14.PACKAGE),'M21_UPGRADE_NOT_INSTALLED')
                    instrument(device,spec['class'],case,nonce,authenticated=lane=='T')
                    report['lanes'][lane]['cases'][case]='PASS'
                report['lanes'][lane]['status']='PASS'
                if lane=='T': report['authenticated_verified']=True
            report['overall']='PASS_SELECTED_M21_LANES'
    except m14.DeviceGateError as exc:
        report.update(failure_code=exc.code,overall='FAILED_OR_BLOCKED')
        report['failure_diagnostics']=getattr(exc,'m21_diagnostic',{})
        running=next((k for k in selected if report['lanes'][k]['status']=='RUNNING'),None)
        if running: report['lanes'][running]['status']='FAILED_OR_BLOCKED'
    except Exception:
        report.update(failure_code='M21_UNEXPECTED_FAILURE',overall='FAILED_OR_BLOCKED')
    store(args.output,report)
    return 0 if report['overall']=='PASS_SELECTED_M21_LANES' else 1


def run_command(argv,code):
    try:
        p=subprocess.run(argv,text=True,capture_output=True,timeout=120,check=False)
    except (OSError,subprocess.TimeoutExpired):
        raise m14.DeviceGateError(code) from None
    require(p.returncode==0,code)
    return p.stdout


def clean_sha(sha):
    return sha.strip().lower().replace(':','')


def signer_certificate(apk):
    """Cryptographically verify the same APK bytes before/after parsing its signer.

    Do not depend on apksigner's version- and locale-sensitive console text.
    The existing M3 signing parser rejects multiple/contradictory v2/v3 signers.
    """
    require(apk.is_file() and not apk.is_symlink(), 'M21_APK_INVALID')
    require(shutil.which('apksigner') is not None, 'M21_APKSIGNER_MISSING')
    with apk.open('rb') as stream:
        before=hashlib.file_digest(stream,'sha256').hexdigest()
    run_command(['apksigner','verify','--verbose','--print-certs',str(apk)],
                'M21_APK_SIGNATURE_INVALID')
    try:
        cert=signing.certificate_sha256(apk)
    except (signing.SigningBlockError, OSError, ValueError):
        raise m14.DeviceGateError('M21_APK_SIGNING_BLOCK_INVALID') from None
    with apk.open('rb') as stream:
        after=hashlib.file_digest(stream,'sha256').hexdigest()
    require(before==after, 'M21_APK_CHANGED_DURING_VERIFICATION')
    require(isinstance(cert,str) and re.fullmatch(r'[0-9a-f]{64}',cert) is not None,
            'M21_APK_CERTIFICATE_INVALID')
    return cert


def verify_release_apk(apk, candidate_sha, release_cert, debug_cert):
    """Never infer release identity from debug artifacts or filename alone."""
    require(apk.is_file() and not apk.is_symlink(), 'M21_RELEASE_APK_MISSING')
    require(apk.stat().st_size in range(1,200*1024*1024+1),'M21_RELEASE_APK_SIZE_INVALID')
    pins=(candidate_sha,release_cert,debug_cert)
    require(all(re.fullmatch(r'[0-9a-fA-F]{64}',x or '') for x in pins),
            'M21_OUT_OF_BAND_PINS_REQUIRED')
    require(clean_sha(release_cert)!=clean_sha(debug_cert),'M21_RELEASE_REUSES_DEBUG_KEY')
    with apk.open('rb') as stream:
        actual=hashlib.file_digest(stream,'sha256').hexdigest()
    require(actual==clean_sha(candidate_sha),'M21_RELEASE_DIGEST_MISMATCH')
    require(shutil.which('apksigner') is not None and shutil.which('aapt') is not None,
            'M21_ANDROID_SIGNING_TOOLS_MISSING')
    require(signer_certificate(apk)==clean_sha(release_cert),
            'M21_RELEASE_CERTIFICATE_MISMATCH')
    badges=run_command(['aapt','dump','badging',str(apk)],'M21_RELEASE_MANIFEST_UNREADABLE')
    require(re.search(r"(?m)^package: name='com\.sdvsync' versionCode='[1-9][0-9]*'",badges)
            and 'application-debuggable' not in badges,
            'M21_RELEASE_PACKAGE_OR_DEBUGGABLE')
    # Security policy is enforced from actual signed bytes, not just Gradle source.
    return dict((name,'PASS') for name in matrix()['R']['cases'])


def run_release(args):
    report=info_report(args.run_id,None,['R'])
    try:
        require(args.release_audit_opt_in,'M21_RELEASE_AUDIT_CONSENT_REQUIRED')
        require(args.release_apk and args.release_cert_sha256 and args.release_apk_sha256 and
                args.debug_cert_sha256,'M21_RELEASE_ARTIFACT_AND_PINS_REQUIRED')
        with tempfile.TemporaryDirectory(prefix='cinderbox-m21-release-') as directory:
            debug_apk,_=attest_ci(args,report,Path(directory))
            require(signer_certificate(debug_apk)==clean_sha(args.debug_cert_sha256),
                    'M21_DEBUG_SIGNER_PROVENANCE_MISMATCH')
        results=verify_release_apk(args.release_apk,args.release_apk_sha256,
                                   args.release_cert_sha256,args.debug_cert_sha256)
        report['lanes']['R'].update(status='PASS',cases=results)
        report['release_candidate_verified']=True
        report['overall']='PASS_SELECTED_M21_LANES'
    except m14.DeviceGateError as exc:
        report.update(failure_code=exc.code,overall='FAILED_OR_BLOCKED')
    except Exception:
        report.update(failure_code='M21_UNEXPECTED_FAILURE',overall='FAILED_OR_BLOCKED')
    store(args.output,report)
    return 0 if report['overall']=='PASS_SELECTED_M21_LANES' else 1


def merge(args):
    report=info_report(None,None,list('UTIR'))
    try:
        require(len(args.merge_reports)>=3,'M21_INSUFFICIENT_REPORTS')
        docs=[m14.read_json(Path(p)) for p in args.merge_reports]
        keys=('repository','github_run_id','source_commit','runner_source_commit',
              'ci_checkout_commit','ci_checkout_ref','apk_sha256','test_apk_sha256')
        first=docs[0]
        for document in docs:
            require(document.get('producer')=='cinderbox-m21-readiness' and
                    document.get('overall')=='PASS_SELECTED_M21_LANES' and
                    document.get('failure_code') is None and document.get('ci')=='PASS' and
                    all(document.get(k)==first.get(k) for k in keys),
                    'M21_MERGE_SOURCE_OR_STATUS_MISMATCH')
        report.update({k:first[k] for k in keys})
        report['ci']='PASS'
        seen=set()
        device=None
        device_transport=None
        for document in docs:
            for lane in document['lanes_requested']:
                require(lane in matrix() and lane not in seen,'M21_MERGE_OVERLAPPING_LANES')
                obj=document['lanes'][lane]
                require(obj['status']=='PASS' and
                        set(obj['cases'])==set(matrix()[lane]['cases']) and
                        all(v=='PASS' for v in obj['cases'].values()),'M21_INCOMPLETE_CASES')
                report['lanes'][lane]=obj
                seen.add(lane)
                if lane != 'R':
                    require(document['install']=='PASS','M21_DEVICE_INSTALL_UNVERIFIED')
                    if device is None:
                        device=document['device']
                        device_transport=document['transport']
                    require(device==document['device'] and
                            device_transport==document['transport'],
                            'M21_DEVICE_OR_TRANSPORT_MISMATCH')
        report['lanes_requested']=sorted(seen)
        report['device']=device
        report['transport']=device_transport
        report['authenticated_verified']= 'T' in seen
        report['release_candidate_verified']= 'R' in seen
        report['install']='PASS' if {'U','T','I'}<=seen else 'INCOMPLETE'
        report['overall']= SUCCESS if seen==set('UTIR') else 'PASS_SELECTED_M21_LANES'
        # Release publication and general qualification require separate decision.
        report['release_qualified']=False
        report['publication_allowed']=False
    except m14.DeviceGateError as exc:
        report.update(failure_code=exc.code,overall='FAILED_OR_BLOCKED')
    except Exception:
        report.update(failure_code='M21_INVALID_REPORT_INPUT',overall='FAILED_OR_BLOCKED')
    store(args.output,report)
    return 0 if report['overall'] in (SUCCESS,'PASS_SELECTED_M21_LANES') else 1


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=ROOT)
    parser.add_argument('--run-id',type=int)
    parser.add_argument('--transport',choices=('termux-root','adb'))
    actions=parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--lane')
    actions.add_argument('--release-audit',action='store_true')
    actions.add_argument('--merge-reports',nargs='+')
    actions.add_argument('--list-lanes',action='store_true')
    parser.add_argument('--output',type=Path)
    for name in ('ui-opt-in','signed-out-opt-in','authenticated-opt-in',
                 'installation-check-opt-in','upgrade-opt-in', 'release-audit-opt-in',
                 'install','allow-replace'):
        parser.add_argument('--'+name,action='store_true')
    parser.add_argument('--release-apk',type=Path)
    parser.add_argument('--release-cert-sha256')
    parser.add_argument('--release-apk-sha256')
    parser.add_argument('--debug-cert-sha256')
    args=parser.parse_args(argv)
    if args.list_lanes:
        print(json.dumps({k:dict(count=len(v['cases']),title=v['title'],
                                  requires_manual_auth=k=='T',requires_release_apk=k=='R')
                          for k,v in matrix().items()},indent=2))
        return 0
    if not args.output: parser.error('--output required')
    if args.merge_reports: return merge(args)
    if not args.run_id: parser.error('--run-id required')
    if args.release_audit: return run_release(args)
    if not args.transport: parser.error('--transport required for device lanes')
    return run_device(args)

if __name__=='__main__': raise SystemExit(main())
