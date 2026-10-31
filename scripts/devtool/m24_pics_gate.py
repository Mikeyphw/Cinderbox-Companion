#!/usr/bin/env python3
"""M24 PICS depot-manifest *identity* source gate; no Steam account or file manifest proof."""
from __future__ import annotations
from ci_workflow_contract import effective_ci_source
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PATHS=(
 'app/src/main/java/com/sdvsync/download/M24DepotManifestIdentity.kt',
 'app/src/main/java/com/sdvsync/steam/SteamContentService.kt',
 'app/src/main/java/com/sdvsync/download/GameDownloadRecovery.kt',
 'app/src/main/java/com/sdvsync/download/GameDownloadService.kt',
 'app/src/test/java/com/sdvsync/download/M24DepotManifestIdentityTest.kt',
 'app/src/androidTest/java/com/sdvsync/qualification/M24PicsManifestIdentityDeviceTest.kt',
 'scripts/devtool/m24_pics_device_run.py',
 '.devtool.toml','.github/workflows/build.yml',
 '.github/workflows/devtool-android-build.yml',
 'docs/security/M3_RELEASE_POLICY.json')
METHODS=("m24p_01ManifestIdentityBoundAndPersisted",
         "m24p_02DepotManifestDriftPreservesPartialStage",
         "m24p_03UnboundManifestCannotQualifyCheckpoint",
         "m24p_04MalformedManifestRejectedWithoutWrites")
def generate(root=ROOT,env=None):
 env=os.environ if env is None else env
 sha=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,timeout=10)
 if sha.returncode or not re.fullmatch(r'[0-9a-f]{40}',sha.stdout.strip()):raise ValueError('GIT_SHA_INVALID')
 if env.get('GITHUB_SHA') and env['GITHUB_SHA']!=sha.stdout.strip():raise ValueError('GITHUB_SHA_MISMATCH')
 if env.get('GITHUB_REPOSITORY') and env['GITHUB_REPOSITORY']!='Mikeyphw/Cinderbox-Companion':raise ValueError('REPO_MISMATCH')
 data={}
 for path in PATHS:
  file=root
  for segment in path.split('/'):
   if segment in ('','.','..'):raise ValueError('PATH_ESCAPE')
   file=file/segment
   if file.is_symlink():raise ValueError('SYMLINK_INPUT')
  if not file.is_file():raise ValueError('SOURCE_MISSING:'+path)
  data[path]=file.read_bytes()
 def source(key):return data[key].decode()
 policy=json.loads(source('docs/security/M3_RELEASE_POLICY.json'))
 if any(policy.get(k) is not False for k in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete')):raise ValueError('RELEASE_POLICY_UNSAFE')
 identity=source(PATHS[0]);steam=source(PATHS[1]);recovery=source(PATHS[2]);service=source(PATHS[3]);device=source(PATHS[5]);runner=source(PATHS[6])
 for phrase in ('fun snapshot(', 'manifestIds.toSortedMap()', 'PICS', 'MessageDigest.getInstance("SHA-256")'):
  if phrase not in identity:raise ValueError('PICS_IDENTITY_CONTRACT_MISSING')
 for phrase in ('manifestFingerprint = snapshot?.fingerprint','depot["manifests"][name]["gid"]'):
  if phrase not in steam:raise ValueError('PICS_DEPOT_DISCOVERY_MISSING')
 for phrase in ('fun bindDepotManifestFingerprint(', 'fun requireDepotManifestFingerprint(', 'pics_depot_manifest_fingerprint', 'StandardCopyOption.ATOMIC_MOVE'):
  if phrase not in recovery:raise ValueError('PICS_JOURNAL_BINDING_MISSING')
 for phrase in ('recovery.bindDepotManifestFingerprint(manifestFingerprint)', 'recovery.requireDepotManifestFingerprint(manifestFingerprint)', 'requireDepotManifestFingerprint(expectedManifestFingerprint)', 'PICS_BOUND_DEPOT_SHA1_UNSIGNED'):
  if phrase not in service:raise ValueError('PICS_LIVE_DRIFT_CHECK_MISSING')
 if tuple(re.findall(r'@Test fun (m24p_\d\d\w+)\s*\(',device))!=METHODS:raise ValueError('ANDROID_CASES_CHANGED')
 for phrase in ('targetContext.cacheDir.canonicalFile','m24pics-owned-'):
  if phrase not in device:raise ValueError('UNSAFE_FIXTURE')
 for phrase in ('SteamClientManager','/storage/emulated/0','su -c','pm clear'):
  if phrase in device:raise ValueError('REAL_SUBSTRATE_FORBIDDEN')
 if not all(m in runner for m in METHODS):raise ValueError('RUNNER_CASES_CHANGED')
 import tomllib
 cfg=tomllib.loads(source('.devtool.toml'))
 if cfg['wrapper']['commands']['m24-pics-check']['workflow']!='m24-pics-check':raise ValueError('WRAPPER_MISSING')
 wf=cfg['targets']['cinderbox']['workflows']['m24-pics-check']
 if [n['id'] for n in wf]!=['security','tests','gate']:raise ValueError('DAG_INVALID')
 for workflow in PATHS[8:10]:
  if effective_ci_source(root,workflow).count('scripts/devtool/m24_pics_gate.py')!=1:raise ValueError('CI_BINDING_MISSING')
 return dict(schema_version=1,producer='cinderbox-m24-pics-identity-source',overall='PASS_PICS_IDENTITY_SOURCE_ONLY',source_commit=sha.stdout.strip(),source_sha256={k:hashlib.sha256(v).hexdigest() for k,v in sorted(data.items())},synthetic_cases=list(METHODS),device_executed=False,steam_entitlement_verified=False,signed_depot_file_manifest_verified=False,real_download_performed=False,installed_source_verified=False,release_qualified=False,publication_allowed=False)
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path);args=ap.parse_args()
 try: report=generate()
 except (OSError,ValueError,KeyError,subprocess.TimeoutExpired) as e:
  print(json.dumps(dict(overall='FAILED_SOURCE_GATE',failure_code=str(e)[:100])));return 1
 data=json.dumps(report,indent=2,sort_keys=True)+'\n'
 if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(data)
 print(data);return 0
if __name__=='__main__':sys.exit(main())
