#!/usr/bin/env python3
"""M23 source/CI/roadmap qualification (not a device or Steam permission receipt)."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
PATHS = (
    'app/src/main/java/com/sdvsync/local/M23InstallationDiscovery.kt',
    'app/src/main/java/com/sdvsync/local/InstallationScanner.kt',
    'app/src/main/java/com/sdvsync/ui/screens/InstallationHealthScreen.kt',
    'app/src/main/java/com/sdvsync/ui/viewmodels/GameDownloadViewModel.kt',
    'app/src/test/java/com/sdvsync/local/M23InstallationDiscoveryTest.kt',
    'scripts/devtool/test_m23_discovery.py',
    'scripts/devtool/m23_discovery_gate.py',
    '.devtool.toml', '.github/workflows/build.yml',
    '.github/workflows/devtool-android-build.yml',
    'docs/security/M3_RELEASE_POLICY.json',
    'docs/devtool/M23_INSTALLATION_DISCOVERY.md',
)

class GateError(ValueError):
    pass

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def safe(root: Path, rel: str) -> bytes:
    target = root
    for part in rel.split('/'):
        if part in ('', '.', '..'):
            raise GateError('UNSAFE_SOURCE_PATH')
        target = target / part
        if target.is_symlink():
            raise GateError('SYMLINK_SOURCE')
    if not target.is_file():
        raise GateError('SOURCE_MISSING')
    return target.read_bytes()

def generate(root: Path = ROOT, env: dict | None = None) -> dict:
    if env is None: env = os.environ
    identity = subprocess.run(['git','rev-parse','HEAD'],cwd=root,text=True,
                              capture_output=True,timeout=10)
    commit = identity.stdout.strip()
    if identity.returncode != 0 or len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise GateError('GIT_IDENTITY_INVALID')
    if env.get('GITHUB_SHA') and env['GITHUB_SHA'] != commit:
        raise GateError('GITHUB_SHA_MISMATCH')
    if env.get('GITHUB_REPOSITORY') and env['GITHUB_REPOSITORY'] != 'Mikeyphw/Cinderbox-Companion':
        raise GateError('GITHUB_REPO_MISMATCH')
    policy = json.loads(safe(root,'docs/security/M3_RELEASE_POLICY.json'))
    for flag in ('release_enabled','device_qualification_complete','publication_enabled','automatic_device_install'):
        if policy.get(flag) is not False:
            raise GateError('UNSAFE_RELEASE_POLICY')
    source = {p:sha(safe(root,p)) for p in PATHS}
    kotlin = safe(root,PATHS[0]).decode()
    scanner = safe(root,PATHS[1]).decode()
    ui = safe(root,PATHS[2]).decode()
    viewmodel = safe(root,PATHS[3]).decode()
    for token in ('MAX_CHILDREN = 256', 'DirectoryStream', 'newDirectoryStream',
                  'UNSAFE_LINK', 'RECOVERY_REVIEW', 'CANDIDATE_UNVERIFIED',
                  'NO_AUTHENTICATED_DEPOT_MANIFEST', 'SMAPI_VERSION_AND_GAME_COMPATIBILITY_UNKNOWN',
                  'downloadAllowed: Boolean = false', 'writesPerformed: Boolean = false'):
        if token not in kotlin:
            raise GateError('SOURCE_CONTRACT_MISSING')
    if 'M23InstallationDiscovery.inspect(' not in scanner or 'StoragePreflight.check(selectedGameDir)' in scanner:
        raise GateError('READ_ONLY_SCAN_NOT_ENFORCED')
    if 'result.discovery' not in ui or 'Not tested for writes' not in ui:
        raise GateError('UI_DISCOVERY_MISSING')
    if 'if (!resume && discovered.gameAlreadyPresent)' not in viewmodel:
        raise GateError('DOWNLOAD_EXISTING_GAME_GUARD_MISSING')
    cfg=tomllib.loads(safe(root,'.devtool.toml').decode())
    target=cfg['targets']['cinderbox']
    flow=target['workflows'].get('m23-check',[])
    if [a['id'] for a in flow] != ['security','m22','tests','inventory']:
        raise GateError('M23_DAG_INVALID')
    jobs=target['jobs']
    if flow[-1]['ref'] != 'job:m23-discovery' or 'm23-discovery' not in jobs:
        raise GateError('M23_JOB_MISSING')
    for workflow in ('.github/workflows/build.yml','.github/workflows/devtool-android-build.yml'):
        content=safe(root,workflow).decode()
        if 'scripts/devtool/m23_discovery_gate.py' not in content or 'test_m23_discovery.py' not in content:
            raise GateError('CI_GATE_MISSING')
    return {
        'schema_version':1, 'producer':'cinderbox-m23-discovery',
        'overall':'PASS_M23_SOURCE_INVENTORY',
        'source_commit':commit,
        'github_source_bound':bool(env.get('GITHUB_SHA')),
        'github_run_id':env.get('GITHUB_RUN_ID'),
        'historical_m14_m21_reexecuted':False,
        'original_receipts_replaced':False,
        'real_device_inventory':'NOT_RUN',
        'saf_root_shizuku_read_permissions':'NOT_VERIFIED',
        'authenticated_game_manifest':'NOT_VERIFIED',
        'm23_device_qualified':False,
        'release_qualified':False, 'publication_allowed':False,
        'source_sha256':source,
        'safety':{'bounded_direct_roots':True,'no_recursive_scan':True,'no_write_probe_in_health_screen':True,
                  'unknown_version_never_green':True, 'download_guard_detects_existing_game':True},
        'result_kind':'HOST_SOURCE_GATE_ONLY'
    }

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    try:
        result=generate()
    except (GateError,KeyError,ValueError,OSError,subprocess.TimeoutExpired) as exc:
        print('M23 SOURCE GATE BLOCKED:',type(exc).__name__,str(exc)[:100],file=sys.stderr)
        return 1
    rendered=json.dumps(result,sort_keys=True,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(rendered)
    print(rendered)
    return 0

if __name__=='__main__': raise SystemExit(main())
