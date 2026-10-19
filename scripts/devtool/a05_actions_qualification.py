#!/usr/bin/env python3
"""A05 Cinderbox GitHub Actions proof. No dispatch, installation, release, or mutation.

The `source` and `record` modes run on the CI host. `verify-run` reads an
existing remote run via authenticated GitHub CLI and verifies its downloaded
artifact bytes; remote status alone never qualifies missing evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REPO = 'Mikeyphw/Cinderbox-Companion'
DEVTOOL_SHA = '08eb13991b5d1c623b64fdd8f9524418ee27207e'
ARTIFACT = 'cinderbox-a05-native-dag'
WORKFLOW = '.github/workflows/devtool-android-build.yml'
FILES = ('RUN_META.json', 'consumer-source.txt', 'devtool-source.txt',
         'devtool-plan.json', 'devtool-preflight.json', 'devtool-invoke.json')
_SHA = re.compile(r'[a-f0-9]{40}\Z')

class ProofError(ValueError):
    pass

def _json(path):
    try:
        data = json.loads(Path(path).read_text('utf-8'))
    except (ValueError, OSError) as exc:
        raise ProofError('Unreadable JSON: ' + str(path)) from exc
    if not isinstance(data, dict):
        raise ProofError('Expected object: ' + str(path))
    return data

def source():
    import tomllib
    cfg = tomllib.loads((ROOT/'.devtool.toml').read_text('utf-8'))
    target = cfg['targets']['cinderbox']
    chain = target['workflows']['m24-verify-ux-check']
    if [(n['id'], n['ref'], n['depends_on']) for n in chain] != [
       ('security', 'job:security-contract', []),
       ('gate', 'job:m24-verify-ux-source', ['security'])]:
        raise ProofError('Native target-local DAG changed')
    if not all(ref.split(':')[1] in target['jobs'] for ref in (n['ref'] for n in chain)):
        raise ProofError('Native DAG references missing target-local jobs')
    for n in chain:
        j=target['jobs'][n['ref'].split(':',1)[1]]
        if (j.get('runner')!='command' or j.get('metadata',{}).get('read_only') is not True
             or j.get('metadata',{}).get('device_required') is True):
            raise ProofError('A05 DAG job is not a read-only native command')
    alias = cfg['wrapper']['commands']['a05-check']
    if (alias.get('target'), alias.get('workflow')) != ('cinderbox', 'm24-verify-ux-check'):
        raise ProofError('Wrapper alias differs from native DAG')
    flow = (ROOT/WORKFLOW).read_text('utf-8')
    if not all(k in flow for k in (
           'a05-native-devtool-dag:', DEVTOOL_SHA, ARTIFACT,
           '--machine-file "$RUNNER_TEMP/devtool-invoke.json" invoke',
           'if: always()', 'contents: read',
           "if: ${{ inputs.a05_mode == 'native-only' || inputs.a05_mode == 'both' }}",
           "if: ${{ inputs.a05_mode != 'native-only' }}",
           "options: ['off', 'native-only', 'both']")):
        raise ProofError('A05 registered workflow missing source-bound execution/evidence')
    lane = flow.split('  a05-native-devtool-dag:', 1)[-1]
    if any(x in lane for x in ('release_qualified: true', 'adb install', 'assembleRelease', 'secrets.', 'contents: write', 'sudo ')):
        raise ProofError('A05 native lane must never claim release qualification or install')
    return {'overall':'PASS_CINDERBOX_A05_SOURCE_CONTRACT', 'source_commit':_git_head(),
            'devtool_sha':DEVTOOL_SHA,'workflow':WORKFLOW,'device_qualified':False,
            'release_qualified':False,'remote_qualified':False}

def _git_head():
    p = subprocess.run(['git','-c',f'safe.directory={ROOT}','-C',str(ROOT),'rev-parse','HEAD'],text=True,capture_output=True)
    if p.returncode or not _SHA.fullmatch(p.stdout.strip()):
        raise ProofError('Consumer source must be an exact accessible Git commit')
    return p.stdout.strip()

def record(out:Path, source_sha:str, devtool_sha:str, repo:str, run_id:int, attempt:int, input_dir:Path):
    if not _SHA.fullmatch(source_sha) or devtool_sha != DEVTOOL_SHA or repo != REPO or run_id < 1 or attempt < 1:
        raise ProofError('Invalid source/run/Devtool identity')
    out.mkdir(parents=True,exist_ok=True)
    present=[]
    for n in ('devtool-plan.json','devtool-preflight.json','devtool-invoke.json'):
        f=input_dir/n
        if f.is_file() and not f.is_symlink():
            (out/n).write_bytes(f.read_bytes());present.append(n)
    (out/'consumer-source.txt').write_text(source_sha+'\n')
    (out/'devtool-source.txt').write_text(devtool_sha+'\n')
    meta={'schema_version':1, 'producer':'cinderbox-a05-native-dag',
          'repository':repo, 'workflow':WORKFLOW,'source_sha':source_sha,
          'devtool_sha':devtool_sha,'run_id':run_id,'run_attempt':attempt,
          'present_machine_files':present, 'complete':len(present)==3,
          'release_qualified':False,'device_qualified':False}
    (out/'RUN_META.json').write_text(json.dumps(meta,sort_keys=True,indent=2)+'\n')
    files=[n for n in FILES if (out/n).is_file()]
    (out/'SHA256SUMS').write_text(''.join(f"{hashlib.sha256((out/n).read_bytes()).hexdigest()}  {n}\n" for n in files))
    return meta

def verify_local(root:Path, *, run_id:int, attempt:int, source_sha:str, require_full:bool=True):
    if not _SHA.fullmatch(source_sha) or run_id<1 or attempt<1:
        raise ProofError('Invalid expected identity')
    if not root.is_dir() or root.is_symlink():raise ProofError('Evidence directory missing/unsafe')
    actual={p.name for p in root.iterdir()}
    if actual - set(FILES) - {'SHA256SUMS'}:
        raise ProofError('Unexpected additional evidence path')
    expected={}
    for line in (root/'SHA256SUMS').read_text('utf-8').splitlines():
        parts=line.split('  ',1)
        if len(parts)!=2 or not re.fullmatch('[a-f0-9]{64}',parts[0]) or parts[1] not in FILES or parts[1] in expected:
            raise ProofError('Malformed SHA256SUMS entry')
        expected[parts[1]]=parts[0]
    required=set(FILES if require_full else FILES[:3])
    if not required.issubset(expected) or set(expected) - set(FILES):
        raise ProofError('Missing or unauthorized evidence files')
    for name,want in expected.items():
        p=root/name
        if p.is_symlink() or not p.is_file() or p.stat().st_size>8_000_000 or hashlib.sha256(p.read_bytes()).hexdigest()!=want:
            raise ProofError('Evidence checksum mismatch: '+name)
    meta=_json(root/'RUN_META.json')
    if (meta.get('producer'),meta.get('repository'),meta.get('workflow'),meta.get('run_id'),meta.get('run_attempt'),
        meta.get('source_sha'),meta.get('devtool_sha')) != (
        'cinderbox-a05-native-dag',REPO,WORKFLOW,run_id,attempt,source_sha,DEVTOOL_SHA):
        raise ProofError('Evidence does not match the selected exact run, attempt or source')
    if meta.get('release_qualified') is not False or meta.get('device_qualified') is not False:
        raise ProofError('Evidence has false release/device qualification')
    if (root/'consumer-source.txt').read_text('utf-8')!=source_sha+'\n' or (root/'devtool-source.txt').read_text('utf-8')!=DEVTOOL_SHA+'\n':
        raise ProofError('Source identity text mismatch')
    if require_full:
        if meta.get('complete') is not True or sorted(meta.get('present_machine_files',[]))!=sorted(FILES[3:]):
            raise ProofError('Machine receipts incomplete')
        for name in FILES[3:]:
            data=_json(root/name)
            if data.get('ok') is not True or data.get('exit_code') != 0 or data.get('result',{}).get('success') is not True:
                raise ProofError('Native machine execution did not pass: '+name)
    return {'overall':'PASS_CINDERBOX_A05_LOCAL_EVIDENCE_VERIFIED', 'run_id':run_id,
            'attempt':attempt,'source_sha':source_sha,'devtool_sha':DEVTOOL_SHA,
            'release_qualified':False,'device_qualified':False}

def _gh_api(endpoint):
    p=subprocess.run(['gh','api',endpoint],capture_output=True,text=True,timeout=35)
    if p.returncode:raise ProofError('GitHub CLI could not read selected resource: '+endpoint)
    try:return json.loads(p.stdout)
    except json.JSONDecodeError as e:raise ProofError('Invalid GitHub response') from e

def verify_run(run_id:int, out:Path, expected_sha:str, mode:str):
    if run_id<1 or not _SHA.fullmatch(expected_sha) or mode not in ('native-only','both'):
        raise ProofError('Exact run ID, source SHA and scope are required')
    base=f'repos/{REPO}/actions/runs/{run_id}'
    run=_gh_api(base)
    if (run.get('id'),run.get('head_sha'),run.get('event'),run.get('status'),
        run.get('path','').split('@')[0].lstrip('/')) != (
         run_id,expected_sha,'workflow_dispatch','completed',WORKFLOW):
        raise ProofError('Remote GitHub run has mismatched source/workflow/event/status')
    if run.get('inputs',{}).get('a05_mode') != mode:
        raise ProofError('Selected workflow input mode does not match the expected A05 mode')
    attempt=run.get('run_attempt')
    if not isinstance(attempt,int) or attempt<1:raise ProofError('Missing exact GitHub run attempt')
    jobs=_gh_api(base+'/jobs?per_page=100')
    items=jobs.get('jobs',[])
    if jobs.get('total_count')!=len(items):raise ProofError('Unpaged job collection')
    matched=[j for j in items if j.get('name') == 'A05 native DAG + EXO evidence' and j.get('run_attempt',attempt)==attempt]
    if len(matched)!=1 or matched[0].get('conclusion')!='success':raise ProofError('Native A05 DAG job not successful')
    if run.get('conclusion')!='success':raise ProofError('GitHub workflow not successful')
    if mode=='both':
        build=[j for j in items if j.get('name') == 'build-debug-apk' and j.get('run_attempt',attempt)==attempt]
        if len(build)!=1 or build[0].get('conclusion')!='success':raise ProofError('Android build job not successful')
    artifacts=_gh_api(base+'/artifacts?per_page=100')
    data=artifacts.get('artifacts',[])
    if artifacts.get('total_count')!=len(data):raise ProofError('Unpaged artifact collection')
    selections=[a for a in data if a.get('name')==ARTIFACT and not a.get('expired',False)]
    if len(selections)!=1 or selections[0].get('workflow_run',{}).get('id') not in (None,run_id):
        raise ProofError('Expected exactly one run-owned unexpired A05 artifact')
    if out.exists():
        if any(out.iterdir()):raise ProofError('Evidence download destination must be empty')
    else:out.mkdir(parents=True)
    p=subprocess.run(['gh','run','download',str(run_id),'--repo',REPO,'--name',ARTIFACT,'--dir',str(out)],
                     text=True,capture_output=True,timeout=120)
    if p.returncode:raise ProofError('Exact artifact download failed: '+p.stderr[-250:])
    receipt=verify_local(out,run_id=run_id,attempt=attempt,source_sha=expected_sha)
    receipt.update({'overall':'PASS_CINDERBOX_A05_GITHUB_RUN_VERIFIED',
                    'remote_workflow_conclusion':run.get('conclusion'),'mode':mode,
                    'artifact_id':selections[0].get('id'),'remote_qualified':True})
    return receipt

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='mode',required=True)
    sub.add_parser('source')
    p=sub.add_parser('record')
    for k in ('evidence-dir','input-dir','repo','sha','devtool-sha','run-id','attempt'):
        p.add_argument('--'+k,required=True)
    p=sub.add_parser('verify-run');p.add_argument('--run-id',required=True,type=int)
    p.add_argument('--sha',required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--mode',choices=('native-only','both'),default='native-only')
    try:
        a=ap.parse_args(argv)
        if a.mode=='source':result=source()
        elif a.mode=='record':result=record(Path(a.evidence_dir),a.sha,a.devtool_sha,a.repo,int(a.run_id),int(a.attempt),Path(a.input_dir))
        else:result=verify_run(a.run_id,a.out,a.sha,a.mode)
        print(json.dumps(result,sort_keys=True));return 0
    except (ProofError, OSError, ValueError, KeyError, TypeError) as e:
        print('CINDERBOX_A05_REFUSED: '+str(e),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
