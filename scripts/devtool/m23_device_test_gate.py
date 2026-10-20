#!/usr/bin/env python3
"""Source-bound M23 Android test APK lane contract; NOT a device-PASS receipt."""
from __future__ import annotations
from ci_workflow_contract import effective_ci_source
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
import tomllib

ROOT=Path(__file__).resolve().parents[2]
CLASS='com.sdvsync.qualification.M23DiscoveryDeviceTest'
TEST='app/src/androidTest/java/com/sdvsync/qualification/M23DiscoveryDeviceTest.kt'
METHODS=(
    'm23_01MissingPrivatePathsAreNotDownloadApproval',
    'm23_02ModernCandidateCannotBecomeVerified',
    'm23_03LegacyModernCollisionStaysUnresolved',
    'm23_04StagingRequiresExplicitRecoveryReview',
    'm23_05UntrustedZipIsOnlyPartial',
    'm23_06SmapiStageNotMisreportedAsHealthy',
    'm23_07SymlinkToFixtureIsRejected',
    'm23_08BoundedEnumerationFailsClosed',
    'm23_09HealthReadDoesNotWriteProbeOrMutateExisting',
    'm23_10SelectedArchiveWrapperIsUnverified',
)
EXPECTED=tuple(m[:6] for m in METHODS)
PATHS=(TEST, 'app/src/androidTest/java/com/sdvsync/qualification/M23CinderboxFirstDeviceTest.kt',
       'app/src/main/java/com/sdvsync/local/M23CinderboxFirstPolicy.kt',
       'app/src/main/java/com/sdvsync/local/M23InstallationDiscovery.kt',
       'app/src/main/java/com/sdvsync/local/InstallationScanner.kt',
       'scripts/devtool/m23_device_test_gate.py', 'scripts/devtool/m23_device_run.py', 'scripts/devtool/test_m23_device_runner.py', '.devtool.toml',
       '.github/workflows/build.yml','.github/workflows/devtool-android-build.yml',
       'docs/security/M3_RELEASE_POLICY.json')
class GateError(ValueError): pass

def generate(root:Path=ROOT,env:dict|None=None)->dict:
    env=os.environ if env is None else env
    proc=subprocess.run(['git','rev-parse','HEAD'],cwd=root,text=True,capture_output=True,timeout=10)
    head=proc.stdout.strip()
    if proc.returncode or not re.fullmatch('[0-9a-f]{40}',head): raise GateError('SOURCE_COMMIT_UNKNOWN')
    if env.get('GITHUB_SHA') and env['GITHUB_SHA'] != head: raise GateError('SOURCE_SHA_MISMATCH')
    if env.get('GITHUB_REPOSITORY') and env['GITHUB_REPOSITORY']!='Mikeyphw/Cinderbox-Companion':
        raise GateError('REPOSITORY_MISMATCH')
    data={}
    for path in PATHS:
        f=root
        for part in path.split('/'):
            if part in ('','.','..'): raise GateError('UNSAFE_SOURCE_PATH')
            f=f/part
            if f.is_symlink(): raise GateError('SYMLINK_SOURCE')
        if not f.is_file(): raise GateError('SOURCE_MISSING')
        data[path]=f.read_bytes()
    policy=json.loads(data['docs/security/M3_RELEASE_POLICY.json'])
    for field in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        if policy.get(field) is not False: raise GateError('RELEASE_POLICY_UNSAFE')
    kotlin=data[TEST].decode()
    methods=re.findall(r'@Test\s+fun\s+(m23_\d\d\w*)\s*\(',kotlin)
    if tuple(methods) != METHODS or len(set(METHODS)) != len(METHODS) or len(METHODS) != 10:
        raise GateError('ANDROID_TEST_MATRIX_CHANGED')
    for term in ('InstrumentationRegistry.getInstrumentation().targetContext',
                 'app.cacheDir.canonicalFile','m23-owned-',
                 'cinderbox-m23-owned-fixture-v1',
                 'M23InstallationDiscovery.inspect(',
                 'InstallationScanner.scan(',
                 'assertFalse(i.downloadAllowed)',
                 'assertFalse(i.modern.verified)'):
        if term not in kotlin: raise GateError('FIXTURE_OR_TEST_SAFETY_CONTRACT_CHANGED')
    if re.search(r'\b(?:am\s+force-stop|pm\s+clear|System\.exit|SteamClientManager|/storage/emulated/0|deleteAll|downloadGame)\b',kotlin):
        raise GateError('DISALLOWED_DEVICE_TEST_OPERATION')
    runner=data['scripts/devtool/m23_device_run.py'].decode()
    if 'parse_m23_instrumentation(output)' not in runner or 'frozenset(METHODS)' not in runner:
        raise GateError('DEVICE_RUNNER_METHOD_MAPPING_MISSING')
    integration = data['app/src/androidTest/java/com/sdvsync/qualification/M23CinderboxFirstDeviceTest.kt'].decode()
    cb_methods = re.findall(r'@Test\s+fun\s+(m23cb_\d\d\w*)\s*\(', integration)
    if len(cb_methods) != 3 or [n[:8] for n in cb_methods] != ['m23cb_01','m23cb_02','m23cb_03']:
        raise GateError('CINDERBOX_DEVICE_TEST_MATRIX_CHANGED')
    for term in ('targetContext.cacheDir.canonicalFile', 'm23-cinderbox-first-',
                 'M23CinderboxFirstPolicy.assess(', 'assertFalse(result.authorizesDownload)'):
        if term not in integration: raise GateError('CINDERBOX_DEVICE_FIXTURE_CONTRACT_CHANGED')
    cfg=tomllib.loads(data['.devtool.toml'].decode())
    job=cfg['targets']['cinderbox']['jobs'].get('m23-device-source',{})
    cmd=job.get('command',[])
    if 'scripts/devtool/m23_device_test_gate.py' not in cmd or job.get('metadata',{}).get('device_required') is not False:
        raise GateError('DEVTOOL_SOURCE_JOB_MISSING')
    graph=cfg['targets']['cinderbox']['workflows'].get('m23-device-check',[])
    if [n.get('id') for n in graph] != ['security','m22','tests','inventory','android_test_source']:
        raise GateError('DEVTOOL_WORKFLOW_MISSING')
    if graph[-1].get('depends_on') != ['inventory']:
        raise GateError('DEVTOOL_DEPENDENCY_MISSING')
    for f in ('.github/workflows/build.yml','.github/workflows/devtool-android-build.yml'):
        workflow=effective_ci_source(root,f)
        if workflow.count('scripts/devtool/m23_device_test_gate.py')!=1:
            raise GateError('CI_DEVICE_TEST_GATE_MISSING')
        if workflow.index('scripts/devtool/m23_device_test_gate.py')>workflow.index('assembleDebugAndroidTest'):
            raise GateError('CI_TEST_PROVENANCE_ORDER')
    return dict(schema_version=1,producer='cinderbox-m23-android-instrumentation-source',
                overall='PASS_SOURCE_ONLY',repository='Mikeyphw/Cinderbox-Companion',
                source_commit=head,github_run_id=env.get('GITHUB_RUN_ID'),
                github_source_bound=bool(env.get('GITHUB_SHA')),
                test_class=CLASS,expected_cases=methods,expected_case_count=len(methods),
                cinderbox_integration_cases=cb_methods,cinderbox_integration_case_count=3,
                installed_apk_verified=False,device_executed=False,device_qualified=False,
                real_user_installation_examined=False,real_game_files_modified=False,
                historical_m14_m22_evidence_replaced=False,release_qualified=False,
                publication_allowed=False,
                source_sha256={k:hashlib.sha256(v).hexdigest() for k,v in data.items()})

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    try:
        report=generate()
    except (GateError, ValueError, OSError, KeyError, subprocess.TimeoutExpired) as e:
        print(json.dumps({'overall':'FAILED_SOURCE_GATE','error_class':type(e).__name__,
                          'error_code':str(e)[:100]}))
        return 1
    result=json.dumps(report,indent=2,sort_keys=True)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(result)
    print(result)
    return 0
if __name__=='__main__':raise SystemExit(main())
