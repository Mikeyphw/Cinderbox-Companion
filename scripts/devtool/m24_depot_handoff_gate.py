#!/usr/bin/env python3
"""Source-bound, fail-closed M24 depot handoff watchdog gate. Does not run Steam."""
import argparse, hashlib, json, os, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
FILES=[
 'app/src/main/java/com/sdvsync/download/M24DepotHandoffPolicy.kt',
 'app/src/main/java/com/sdvsync/download/GameDownloadService.kt',
 'app/src/main/java/com/sdvsync/download/GameDownloadManager.kt',
 'app/src/main/java/com/sdvsync/ui/screens/GameDownloadScreen.kt',
 'scripts/devtool/test_m24_depot_handoff_gate.py',
 '.github/workflows/build.yml', '.devtool.toml',
 'docs/security/M3_RELEASE_POLICY.json',
]

def validate(root=ROOT, env=None):
    env=os.environ if env is None else env
    refs={}
    for rel in FILES:
        q=root
        for part in rel.split('/'):
            if part in ('','.','..'):raise ValueError('INVALID_SOURCE_PATH')
            q=q/part
            if q.is_symlink():raise ValueError('SYMLINK_SOURCE:'+rel)
        if not q.is_file():raise ValueError('SOURCE_MISSING:'+rel)
        refs[rel]=q.read_bytes()
    get=lambda p:refs[p].decode()
    src=get(FILES[0]);svc=get(FILES[1]);manager=get(FILES[2]);ui=get(FILES[3]);ci=get(FILES[5]);cfg=get(FILES[6])
    for token in ('FIRST_CONTENT_TIMEOUT_MS = 240_000L','TRANSFER_STALL_TIMEOUT_MS = 300_000L',
                  'STEAM_DEPOT_REPORTED_FAILURE','STEAM_DEPOT_FIRST_CONTENT_TIMEOUT',
                  'STEAM_DEPOT_CONTENT_STALLED','fun safePhase('):
        if token not in src:raise ValueError('WATCHDOG_POLICY_MISSING:'+token)
    for token in ('depotContentObserved.set(true)','lastDepotContentMs.set(SystemClock.elapsedRealtime())',
                  'M24DepotHandoffPolicy.safePhase(message)', 'M24DepotHandoffPolicy.failureCode(',
                  'currentCoroutineContext().ensureActive()', 'completion.await()',
                  'downloader.getCompletion()', 'delay(1_000L)',
                  'recovery.requireSteamBuildId(expectedBuildId)', 'recovery.requireDepotManifestFingerprint(manifestFingerprint)',
                  'M24DepotManifestCrosscheck.verify(root, depotIds, completedDepots)'):
        if token not in svc:raise ValueError('SERVICE_BOUNDARY_MISSING:'+token)
    if 'downloader.awaitCompletion()' in svc:raise ValueError('BLOCKING_WAIT_REMAINS')
    if 'AppLogger.d(TAG, "Status: $message")' in svc:raise ValueError('RAW_SDK_STATUS_LOGGED')
    if 'val depotPhase: String = ""' not in manager:raise ValueError('PROGRESS_MODEL_MISSING')
    if 'depotPhase.ifBlank' not in ui or 'Waiting for depot progress…' in ui:raise ValueError('UI_STATUS_GATE_MISSING')
    if ci.count('test_m24_depot_handoff_gate.py') != 1 or ci.count('m24_depot_handoff_gate.py --output')!=1:raise ValueError('CI_GATE_MISSING')
    import tomllib
    settings=tomllib.loads(cfg)
    if settings['wrapper']['commands']['m24-handoff-check']['workflow'] != 'm24-handoff-check':raise ValueError('WRAPPER_COMMAND_MISSING')
    dag=settings['targets']['cinderbox']['workflows']['m24-handoff-check']
    if [n['id'] for n in dag]!=['security','tests','gate']:raise ValueError('DEVTOOL_DAG_INVALID')
    policy=json.loads(get(FILES[-1]))
    if any(policy.get(k) is not False for k in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete')):raise ValueError('RELEASE_POLICY_UNSAFE')
    sha=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True,timeout=10)
    if sha.returncode or not re.fullmatch(r'[0-9a-f]{40}',sha.stdout.strip()):raise ValueError('GIT_SHA_INVALID')
    if env.get('GITHUB_SHA') and env['GITHUB_SHA']!=sha.stdout.strip():raise ValueError('GITHUB_SHA_MISMATCH')
    return {'schema_version':1,'producer':'cinderbox-m24-depot-handoff-source','overall':'PASS_M24_DEPOT_HANDOFF_SOURCE',
        'source_sha':sha.stdout.strip(),'files_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in sorted(refs.items())},
        'live_download_tested':False,'steam_entitlement_verified':False,'signed_steam_manifest_verified':False,
        'historical_m24_evidence_replaced':False,'game_files_modified':False,'release_qualified':False,'publication_allowed':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    a=parser.parse_args()
    try:r=validate()
    except (OSError,ValueError,KeyError,subprocess.TimeoutExpired) as exc:
        print(json.dumps({'overall':'FAILED_SOURCE_GATE','failure_code':str(exc)[:160]}));return 1
    content=json.dumps(r,indent=2,sort_keys=True)+'\n'
    if a.output:
        if a.output.is_symlink():return 1
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(content)
    print(content);return 0
if __name__=='__main__':raise SystemExit(main())
