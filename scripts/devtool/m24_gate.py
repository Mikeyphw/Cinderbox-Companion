#!/usr/bin/env python3
"""Source-bound M24 code/CI/evidence contract. Does not authorize a live Steam operation."""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys
from pathlib import Path
import tomllib
ROOT=Path(__file__).resolve().parents[2]
PATHS=(
    'app/src/main/java/com/sdvsync/download/M24SteamSelectionPolicy.kt',
    'app/src/main/java/com/sdvsync/download/GameDownloadRecovery.kt',
    'app/src/main/java/com/sdvsync/download/GameDownloadManager.kt',
    'app/src/main/java/com/sdvsync/download/GameDownloadService.kt',
    'app/src/main/java/com/sdvsync/ui/viewmodels/GameDownloadViewModel.kt',
    'app/src/main/java/com/sdvsync/ui/screens/GameDownloadScreen.kt',
    'app/src/test/java/com/sdvsync/download/M24SteamSelectionPolicyTest.kt',
    'app/src/test/java/com/sdvsync/download/M24SteamBuildCheckpointTest.kt',
    'app/src/androidTest/java/com/sdvsync/qualification/M24SteamDownloadSafetyDeviceTest.kt',
    'scripts/devtool/m24_device_run.py','scripts/devtool/m24_gate.py',
    'scripts/devtool/test_m24_gate.py',
    '.devtool.toml','.github/workflows/build.yml',
    '.github/workflows/devtool-android-build.yml',
    'docs/security/M3_RELEASE_POLICY.json')
METHODS=('m24_01AuthenticatedBranchBuildGateFailClosed',
    'm24_02FreshCheckpointCannotResumeWithoutBuild',
    'm24_03BoundBuildSurvivesColdRecovery',
    'm24_04DriftLeavesOwnedPartialBytesUntouched')
def require(ok,message):
    if not ok:raise ValueError(message)
def generate(root=ROOT,env=None):
    env=os.environ if env is None else env
    sha=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,timeout=10)
    require(sha.returncode==0 and re.fullmatch('[0-9a-f]{40}',sha.stdout.strip()),'GIT_SHA_INVALID')
    head=sha.stdout.strip()
    require(not env.get('GITHUB_SHA') or env['GITHUB_SHA']==head,'GITHUB_SHA_MISMATCH')
    require(not env.get('GITHUB_REPOSITORY') or env['GITHUB_REPOSITORY']=='Mikeyphw/Cinderbox-Companion','REPO_MISMATCH')
    content={}
    for path in PATHS:
        f=root
        for part in path.split('/'):
            require(part not in ('','.','..'),'UNSAFE_PATH')
            f=f/part
            require(not f.is_symlink(),'SYMLINK_INPUT')
        require(f.is_file(),'SOURCE_MISSING:'+path)
        content[path]=f.read_bytes()
    get=lambda p:content[p].decode()
    policy=json.loads(get('docs/security/M3_RELEASE_POLICY.json'))
    require(all(policy.get(k) is False for k in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete')),'RELEASE_POLICY_UNSAFE')
    rec=get('app/src/main/java/com/sdvsync/download/GameDownloadRecovery.kt')
    mgr=get('app/src/main/java/com/sdvsync/download/GameDownloadManager.kt')
    svc=get('app/src/main/java/com/sdvsync/download/GameDownloadService.kt')
    ui=get('app/src/main/java/com/sdvsync/ui/viewmodels/GameDownloadViewModel.kt')
    screen=get('app/src/main/java/com/sdvsync/ui/screens/GameDownloadScreen.kt')
    for term in ('fun bindSteamBuildId(', 'fun requireSteamBuildId(', 'steam_build_id', 'current.steamBuildId == 0L || current.steamBuildId == buildId'):
        require(term in rec,'CHECKPOINT_BINDING_MISSING')
    for term in ('require(verifyAfterDownload && branchBuildId > 0L)',
                 'recovery.bindSteamBuildId(branchBuildId)','recovery.requireSteamBuildId(branchBuildId)',
                 'expectedBuildId = branchBuildId', 'StoragePlanner.downloadPlan(directory, estimatedPayloadBytes).sufficient == true'):
        require(term in mgr,'MANAGER_GATE_MISSING')
    for term in ('recheckBranch()', 'SteamContentService(clientManager)',
                 'GameDownloadRecovery(filesDir).requireSteamBuildId(expectedBuildId)',
                 'verifyFiles(installDir, completedFiles)',
                 'LOCAL_SHA256_ONLY_MANIFEST_UNATTESTED',
                 'StoragePlanner.downloadPlan(installRoot, estimatedPayloadBytes).sufficient == true'):
        require(term in svc,'SERVICE_GATE_MISSING')
    require(svc.count('recheckBranch()')>=3,'PRE_AND_POST_PICS_CHECK_REQUIRED')
    require('capacity.sufficient == false || capacity.sufficient == null' in ui,'UNKNOWN_CAPACITY_MUST_BLOCK')
    require('selectedBranchInfo.buildId' in ui and '!current.verifyAfterDownload' in ui,'UI_LIVE_GUARD_MISSING')
    require('enabled = false' in screen and 'LOCAL_SHA256_ONLY_MANIFEST_UNATTESTED' in screen,'USER_STATUS_UNSAFE')
    kt=get('app/src/androidTest/java/com/sdvsync/qualification/M24SteamDownloadSafetyDeviceTest.kt')
    discovered=re.findall(r'@Test fun (m24_\d\d\w+)\s*\(',kt)
    require(tuple(discovered)==METHODS,'DEVICE_CASE_MATRIX_CHANGED')
    for x in ('targetContext.cacheDir.canonicalFile','m24-owned-', 'GameDownloadRecovery(owner)'):
        require(x in kt,'PRIVATE_FIXTURE_CONTRACT_CHANGED')
    for x in ('SteamClientManager','/storage/emulated/0','am force-stop','pm clear'):
        require(x not in kt,'DEVICE_REAL_SUBSTRATE_FORBIDDEN')
    cfg=tomllib.loads(get('.devtool.toml'))
    wf=cfg['targets']['cinderbox']['workflows'].get('m24-check',[])
    require([n['id'] for n in wf]==['security','m22','m23','tests','gate'],'DAG_NOT_REGISTERED')
    require(wf[-1].get('depends_on')==['tests'],'DAG_ORDER_INVALID')
    require(cfg['wrapper']['commands']['m24-check']['workflow']=='m24-check','WRAPPER_ALIAS_MISSING')
    for pth in ('.github/workflows/build.yml','.github/workflows/devtool-android-build.yml'):
        ci=get(pth)
        require(ci.count('scripts/devtool/m24_gate.py')==1,'CI_GATE_NOT_BOUND')
        require(ci.count('test_m24_gate.py')==1,'CI_HOST_TESTS_NOT_BOUND')
        require(ci.index('scripts/devtool/m24_gate.py')<ci.index('assembleDebugAndroidTest'),'CI_ORDER_INVALID')
    return dict(schema_version=1,producer='cinderbox-m24-host-source',repository='Mikeyphw/Cinderbox-Companion',
                source_commit=head,github_run_id=env.get('GITHUB_RUN_ID'),
                github_source_bound=bool(env.get('GITHUB_SHA')),
                overall='PASS_SOURCE_ONLY',source_sha256={k:hashlib.sha256(v).hexdigest() for k,v in sorted(content.items())},
                synthetic_device_cases=list(METHODS),device_executed=False,installed_source_verified=False,
                authenticated_steam_tested=False,licensed_depot_manifest_verified=False,
                atomic_game_install_committed=False,real_game_modified=False,
                historical_m14_m23_evidence_replaced=False,device_qualified=False,
                release_qualified=False,publication_allowed=False,
                obligations=['STEAM_LICENSE_AND_SIGNED_MANIFEST_EVIDENCE','REAL_CONSENTED_DOWNLOAD',
                             'PROVEN_APK_IDENTITY','ATOMIC_GAME_DIRECTORY_COMMIT','PROCESS_DEATH_RECOVERY'])
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    try: report=generate()
    except (OSError,ValueError,KeyError,subprocess.TimeoutExpired) as e:
        print(json.dumps(dict(overall='FAILED_SOURCE_GATE',error_code=str(e)[:100])))
        return 1
    data=json.dumps(report,indent=2,sort_keys=True)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(data)
    print(data)
    return 0
if __name__=='__main__':sys.exit(main())
