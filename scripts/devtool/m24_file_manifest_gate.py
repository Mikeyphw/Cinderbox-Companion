#!/usr/bin/env python3
"""M24 bounded cached-depot-file content proof source gate. No live Steam test here."""
from pathlib import Path
import hashlib, json, os, re, subprocess, sys, argparse
ROOT=Path(__file__).resolve().parents[2]
FILES=(
'app/src/main/java/com/sdvsync/download/M24DepotFileProof.kt',
'app/src/main/java/com/sdvsync/download/M24DepotManifestCrosscheck.kt',
'app/src/main/java/com/sdvsync/download/GameDownloadService.kt',
'app/src/main/java/com/sdvsync/steam/SteamContentService.kt',
'app/src/androidTest/java/com/sdvsync/qualification/M24FileManifestProofDeviceTest.kt',
'scripts/devtool/m24_file_manifest_device_run.py',
'scripts/devtool/test_m24_file_manifest_gate.py',
'.devtool.toml', '.github/workflows/build.yml',
'.github/workflows/devtool-android-build.yml',
'docs/security/M3_RELEASE_POLICY.json',
)
METHODS=("m24f_01OwnedStageMatchesManifest", "m24f_02AlteredBytesCannotQualify",
         "m24f_03UnexpectedFileCannotQualify", "m24f_04TraversalIsRejectedWithoutOutsideWrites")
def generate(root=ROOT, env=None):
    env=os.environ if env is None else env
    check=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,timeout=10)
    if check.returncode or re.fullmatch(r'[0-9a-f]{40}',check.stdout.strip()) is None:raise ValueError('GIT_SHA_INVALID')
    sha=check.stdout.strip()
    if env.get('GITHUB_SHA') and env['GITHUB_SHA']!=sha:raise ValueError('GITHUB_SHA_MISMATCH')
    if env.get('GITHUB_REPOSITORY') and env['GITHUB_REPOSITORY']!='Mikeyphw/Cinderbox-Companion':raise ValueError('REPO_MISMATCH')
    raw={}
    for path in FILES:
        dest=root
        for part in path.split('/'):
            if part in ('','.','..'):raise ValueError('INVALID_PATH')
            dest=dest/part
            if dest.is_symlink():raise ValueError('SYMLINK_INPUT')
        if not dest.is_file():raise ValueError('MISSING_SOURCE:'+path)
        raw[path]=dest.read_bytes()
    source=lambda name:raw[name].decode()
    policy=json.loads(source('docs/security/M3_RELEASE_POLICY.json'))
    if any(policy.get(k) is not False for k in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete')):raise ValueError('RELEASE_POLICY_UNSAFE')
    proof=source(FILES[0]);adapter=source(FILES[1]);service=source(FILES[2]);steam=source(FILES[3]);device=source(FILES[4]);runner=source(FILES[5]);cfg=source('.devtool.toml')
    for phrase in ('fun verify(stage:', 'SHA-1', 'Unsafe depot manifest path', 'Missing or unlisted staged files','Files.isSymbolicLink'):
        if phrase not in proof:raise ValueError('CONTENT_PROOF_CONTRACT_MISSING')
    for phrase in ('Util.loadManifestFromFile(', 'manifest.manifestGID == gid.toLong()', 'M24DepotFileProof.verify(stage, expected)', 'Conflicting depot files', 'completedDepots: Set<Int>? = null'):
        if phrase not in adapter:raise ValueError('DEPOT_ADAPTER_CONTRACT_MISSING')
    for phrase in ('M24DepotManifestCrosscheck.verify(root, depotIds, completedDepots)', 'M24DepotManifestCrosscheck.verify(destination, depotIds, completedDepots)', 'PICS_BOUND_DEPOT_SHA1_UNSIGNED', 'recheckBranch()'):
        if phrase not in service:raise ValueError('PRE_PROMOTION_BOUNDARY_MISSING')
    if 'depotManifestIds = if (snapshot != null) manifestIds else emptyMap()' not in steam:raise ValueError('PICS_DEPOT_MAP_MISSING')
    methods=tuple(re.findall(r'@Test fun (m24f_\d\d\w+)\s*\(', device))
    if methods!=METHODS or any(m not in runner for m in METHODS):raise ValueError('ANDROID_METHOD_MATRIX_CHANGED')
    if 'targetContext.cacheDir.canonicalFile' not in device or '/storage/emulated/0' in device:raise ValueError('DEVICE_SUBSTRATE_UNSAFE')
    import tomllib
    settings=tomllib.loads(cfg)
    if settings['wrapper']['commands']['m24-file-check']['workflow']!='m24-file-check':raise ValueError('DEVTOOL_ALIAS_MISSING')
    nodes=settings['targets']['cinderbox']['workflows']['m24-file-check']
    if [node['id'] for node in nodes]!=['security','tests','gate']:raise ValueError('DEVTOOL_DAG_INVALID')
    for ci in FILES[8:10]:
        if source(ci).count('scripts/devtool/m24_file_manifest_gate.py')!=1:raise ValueError('CI_GATE_NOT_BOUND')
    return dict(schema_version=1,producer='cinderbox-m24-depot-file-proof-source',overall='PASS_M24_DEPOT_FILE_PROOF_SOURCE',source_sha=sha,
                source_sha256={k:hashlib.sha256(v).hexdigest() for k,v in sorted(raw.items())},synthetic_cases=list(METHODS),
                device_executed=False,installed_source_verified=False,live_download_performed=False,
                steam_entitlement_verified=False,signed_steam_manifest_verified=False,
                cached_depot_manifest_crosscheck_source_present=True,real_game_modified=False,
                device_qualified=False,release_qualified=False,publication_allowed=False)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path);args=ap.parse_args()
    try: data=generate()
    except (ValueError,KeyError,OSError,subprocess.TimeoutExpired) as e:
        print(json.dumps(dict(overall='FAILED_SOURCE_GATE',failure_code=str(e)[:140])));return 1
    result=json.dumps(data,indent=2,sort_keys=True)+'\n'
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(result)
    print(result);return 0
if __name__=='__main__':sys.exit(main())
