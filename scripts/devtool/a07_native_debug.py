#!/usr/bin/env python3
"""A07 fail-closed native debug build source and exact host evidence contract.

Local receipts are self-reported; GitHub run/artifact ownership must be verified
independently before any hosted qualification verdict.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
REPO = 'Mikeyphw/Cinderbox-Companion'
PIN = '409c5527532eaa1ee62b8111e030732d3f9e2791'
WORKFLOW = '.github/workflows/devtool-android-build.yml'
MACHINE = ('a07-plan.json', 'a07-preflight.json', 'a07-invoke.json')
PROOFS = ('debug.apk', 'SHA256SUMS', 'M3_PROVENANCE.json', 'M13_QUALIFICATION.json')
SHA40 = re.compile(r'[a-f0-9]{40}\Z')
SHA64 = re.compile(r'[a-f0-9]{64}\Z')

class Refused(ValueError):
    pass

def insist(ok: bool, reason: str):
    if not ok: raise Refused(reason)

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def read_json(path: Path, cap=8_000_000) -> dict:
    insist(path.is_file() and not path.is_symlink() and path.stat().st_size<=cap,'Missing/unsafe evidence '+path.name)
    try: doc=json.loads(path.read_text('utf8'))
    except (ValueError,UnicodeError) as exc: raise Refused('Invalid JSON '+path.name) from exc
    insist(type(doc) is dict,'Invalid JSON object '+path.name)
    return doc

def sha_sum_file(files: list[Path], root: Path) -> str:
    return ''.join(f'{digest(f)}  {f.relative_to(root)}\n' for f in files)

def source_contract(root:Path=ROOT) -> None:
    cfg=tomllib.loads((root/'.devtool.toml').read_text('utf8'))
    c=cfg['targets']['cinderbox']
    nodes=c['workflows']['build']
    insist([(n['id'],n['ref'],n['depends_on']) for n in nodes]==[
        ('security','job:security-contract',[]),
        ('apk','job:debug-apk',['security']),
        ('verify','job:verify-debug-apk',['apk'])], 'Devtool native build DAG drift')
    j=c['jobs']
    insist(j['security-contract']['runner']=='command' and
           j['security-contract']['command']==['python3','scripts/devtool/check_security_contract.py'] and
           j['security-contract']['metadata']['read_only'] is True,'Security job drift')
    insist(j['debug-apk']['runner']=='android' and
           j['debug-apk']['gradle_tasks']==[':app:assembleDebug'] and
           j['debug-apk']['metadata']['release_signed'] is False, 'Debug job drift')
    insist(j['verify-debug-apk']['runner']=='command' and
           j['verify-debug-apk']['command']==['python3','scripts/devtool/verify_debug_apk.py'] and
           j['verify-debug-apk']['metadata']['read_only'] is True,'APK verification job drift')
    flow=(root/WORKFLOW).read_text('utf8')
    insist('workflow_dispatch:' in flow and
           'permissions:\n  contents: read' in flow and
           "options: ['off', 'native-only', 'both']" in flow and
           'a07_native_build:' in flow and
           'type: boolean' in flow and
           'default: false' in flow, 'A05 choice/A07 boolean dispatch drift')
    insist("if: ${{ inputs.a07_native_build == true && inputs.a05_mode == 'native-only' }}" in flow,
           'A07 dispatch must disable the legacy build')
    insist(flow.count('  a07-native-debug-build:')==1 and
           flow.index('  a07-native-debug-build:') < flow.index('  a05-native-devtool-dag:'),
           'A07 job must precede unchanged A05 job')
    s=flow.split('  a07-native-debug-build:',1)[-1].split('  # A05: source-only',1)[0]
    # GitHub does not expose the runner context in jobs.<job_id>.env.
    # Keep runner.temp exclusively in individual step env mappings.
    guard_a07_runner_environment(s)
    guard_a07_sdk_setup(s)
    required=(f'A07_DEVTOOL_SHA: {PIN}', 'if: always()', 'if: success()',
              'plan --target cinderbox build --json',
              'preflight --target cinderbox --workflow build --json',
              'invoke --target cinderbox build', 'm16_debug_signing.py provision',
              'm16_debug_signing.py verify', 'm3_build_evidence.py generate',
              'm13_qualification.py finalize', 'core_cli_schema.json',
              'a07_native_debug.py verify-local', 'cinderbox-a07-debug-apk',
              'cinderbox-a07-machine-evidence')
    insist(all(x in s for x in required),'A07 hosted build source contract missing')
    forbidden=('PYTHONPATH=', 'export PYTHONPATH', 'assembleRelease', 'publish_release',
               'adb install', 'contents: write', 'upload-release-asset', 'device_qualified: true',
               'release_qualified: true', 'pull_request:', 'push:', 'sudo ')
    insist(not any(x in s for x in forbidden),'A07 hosted lane has forbidden operation')
    insist(s.count('uses: actions/upload-artifact@')==2,'Unexpected uploaded artifact type')
    insist('CINDERBOX_DEBUG_KEYSTORE_B64' in s and 'CINDERBOX_DEBUG_CERT_SHA256' in s,
           'M16 signer credential or pin missing')

def guard_a07_runner_environment(job: str) -> None:
    # Inspect only the A07 job, never A05/legacy jobs (which have their own scope).
    header, marker, body = job.partition('    steps:\n')
    insist(bool(marker), 'A07 job steps block missing')
    insist('runner.temp' not in header and 'runner.' not in header,
           'runner context is unavailable in A07 job-level expressions')
    expected = 'DEVTOOL_XDG_DIR: ${{ runner.temp }}/devtool-a07-state'
    insist(body.count(expected) == 2,
           'A07 plan and invoke steps must each set isolated runner temp state')
    plan = body.split('      - name: Native build DAG plan and preflight\n', 1)
    invoke = body.split('      - name: Invoke native security to APK to verification DAG\n', 1)
    insist(len(plan) == 2 and len(invoke) == 2,
           'A07 state consumers are missing')
    insist(plan[1].split('      - name:', 1)[0].count(expected) == 1 and
           invoke[1].split('      - name:', 1)[0].count(expected) == 1,
           'A07 state env must be step-scoped for plan and invoke')

def guard_a07_sdk_setup(job: str) -> None:
    """Reject retired Android SDK `tools` package before dispatch.

    android-actions/setup-android@v3 defaults to the removed 'tools platform-tools'
    when `with.packages` is missing. Require the reviewed supported package.
    """
    step_name = '      - name: Set up Android SDK\n'
    parts = job.split(step_name)
    insist(len(parts) == 2, 'A07 Android SDK setup step missing/ambiguous')
    block = parts[1].split('      - name:', 1)[0]
    insist(block == ('        uses: android-actions/setup-android@v3\n'
                     '        with:\n'
                     '          packages: platform-tools\n'),
           'A07 SDK setup must explicitly request supported platform-tools only')

def check_machine(directory:Path)->None:
    for f in MACHINE:
        doc=read_json(directory/f)
        insist(doc.get('ok') is True and doc.get('exit_code')==0 and
               doc.get('machine',{}).get('operation',{}).get('status')=='ok',
               'Non-successful native machine phase: '+f)
    invocation=read_json(directory/'a07-invoke.json')
    detail=invocation.get('machine',{}).get('operation',{}).get('detail','')
    insist(all(f'job:cinderbox.{name}: ok' in detail for name in
               ('security-contract','debug-apk','verify-debug-apk')),
           'Native build DAG has missing/failed nodes')

def proof(apks:Path, sha:str)->str:
    insist(apks.is_dir() and not apks.is_symlink(),'Missing APK evidence directory')
    insist({p.name for p in apks.iterdir()}==set(PROOFS),'Unexpected/missing APK artifacts')
    for name in PROOFS:
        f=apks/name
        insist(f.is_file() and not f.is_symlink(),'Unsafe APK evidence: '+name)
    apk=apks/'debug.apk'
    insist(4096<=apk.stat().st_size<=256*1024*1024,'APK invalid size')
    want=digest(apk)
    insist((apks/'SHA256SUMS').read_text('utf8')==f'{want}  debug.apk\n','APK SHA256SUMS mismatch')
    m3=read_json(apks/'M3_PROVENANCE.json')
    m13=read_json(apks/'M13_QUALIFICATION.json')
    insist(m3.get('repository')==REPO and m3.get('source_commit')==sha and
           m3.get('variant')=='debug' and m3.get('format')=='apk' and
           m3.get('evidence_kind')=='ci-build-self-report','M3 source mismatch')
    insist(all(m3.get(x) is False for x in
           ('qualified_release','publication_allowed','reproducibility_proven','device_qualified')),
           'False M3 device/release claim')
    info=m3.get('apk') or {}
    insist(info.get('filename')=='debug.apk' and info.get('sha256')==want and
           info.get('size_bytes')==apk.stat().st_size and
           info.get('package_name')=='com.sdvsync' and
           info.get('signature_verified') is True and info.get('debug_signed') is True and
           SHA64.fullmatch(info.get('signing_certificate_sha256','')) is not None,
           'M3 APK signer/hash proof incomplete')
    insist(m13.get('producer')=='cinderbox-m13' and m13.get('source_commit')==sha and
           m13.get('artifact_sha256')==want and
           m13.get('apk_integrity')=='PASS_SHA256_MATCHES_M3' and
           m13.get('release_qualified') is False and
           m13.get('device_qualified') is False,
           'M13 source/qualification mismatch')
    return want

def record(indir:Path, out:Path, apks:Path|None, incomplete:bool):
    sha=os.environ.get('GITHUB_SHA','')
    insist(SHA40.fullmatch(sha) is not None and os.environ.get('GITHUB_REPOSITORY')==REPO,
           'Untrusted GitHub identity')
    run=int(os.environ.get('GITHUB_RUN_ID','0'))
    attempt=int(os.environ.get('GITHUB_RUN_ATTEMPT','0'))
    insist(run>0 and attempt>0,'Invalid GitHub run identity')
    insist(not out.is_symlink(),'Evidence directory symlink forbidden')
    out.mkdir(parents=True, exist_ok=True)
    copied=[]
    for name in MACHINE:
        p=indir/name
        if p.is_file() and not p.is_symlink() and p.stat().st_size<=8_000_000:
            (out/name).write_bytes(p.read_bytes());copied.append(name)
    complete=not incomplete and len(copied)==len(MACHINE) and apks is not None
    apksha=None
    if complete:
        check_machine(out)
        apksha=proof(apks,sha)
    rec={'schema_version':1,'producer':'cinderbox-a07-native-debug',
         'repository':REPO,'workflow':WORKFLOW,'source_sha':sha,
         'run_id':run,'run_attempt':attempt,'devtool_sha':PIN,
         'present_machine_files':copied,'complete':bool(complete),
         'apk_sha256':apksha,'android_device_qualified':False,
         'release_qualified':False,'github_run_qualified':False}
    (out/'RUN_META.json').write_text(json.dumps(rec,sort_keys=True,indent=2)+'\n')
    files=[out/n for n in (*MACHINE,'RUN_META.json') if (out/n).is_file()]
    (out/'SHA256SUMS').write_text(sha_sum_file(files,out))
    return rec

def verify_local(indir:Path, apks:Path,sha:str,run:int,attempt:int):
    insist(SHA40.fullmatch(sha) is not None and run>0 and attempt>0,
           'Invalid trusted run identity')
    insist(indir.is_dir() and not indir.is_symlink(),'Unsafe machine proof dir')
    insist({p.name for p in indir.iterdir()}==set(MACHINE)|{'RUN_META.json','SHA256SUMS'},
           'Missing/extra machine evidence file')
    check_machine(indir)
    sums=(indir/'SHA256SUMS').read_text('utf8')
    insist(sums==sha_sum_file([indir/f for f in (*MACHINE,'RUN_META.json')],indir),
           'Machine checksums corrupted')
    meta=read_json(indir/'RUN_META.json')
    insist((meta.get('producer'),meta.get('repository'),meta.get('workflow'),
           meta.get('source_sha'),meta.get('run_id'),meta.get('run_attempt'),
           meta.get('devtool_sha'))==('cinderbox-a07-native-debug',REPO,WORKFLOW,sha,run,attempt,PIN),
           'Host evidence not bound to requested exact run')
    insist(meta.get('complete') is True and meta.get('present_machine_files')==list(MACHINE) and
           all(meta.get(x) is False for x in ('android_device_qualified','release_qualified','github_run_qualified')),
           'Incomplete/false qualification claims')
    actual=proof(apks,sha)
    insist(meta.get('apk_sha256')==actual,'Evidence APK digest mismatch')
    return {'overall':'PASS_CINDERBOX_A07_LOCAL_ARTIFACT_CONSISTENCY',
            'source_sha':sha,'run_id':run,'run_attempt':attempt,
            'devtool_sha':PIN,'apk_sha256':actual,
            'github_run_qualified':False,'android_device_qualified':False,'release_qualified':False}

def _gh_json(endpoint:str)->dict:
    p=subprocess.run(['gh','api',endpoint],capture_output=True,text=True,timeout=60)
    insist(p.returncode==0,'GitHub API call failed: '+endpoint)
    try: doc=json.loads(p.stdout)
    except ValueError as exc: raise Refused('Invalid GitHub response') from exc
    insist(type(doc) is dict,'GitHub response is not an object')
    return doc

def verify_run(run_id:int,attempt:int,sha:str)->dict:
    insist(run_id>0 and attempt>0 and SHA40.fullmatch(sha) is not None,'Exact run SHA/attempt required')
    prefix='repos/'+REPO+'/actions/runs/'+str(run_id)
    run=_gh_json(prefix)
    insist(run.get('id')==run_id and run.get('run_attempt')==attempt and
           run.get('head_sha')==sha and run.get('event')=='workflow_dispatch' and
           run.get('status')=='completed' and run.get('conclusion')=='success' and
           run.get('repository',{}).get('full_name')==REPO and
           run.get('path','').endswith(WORKFLOW), 'GitHub run identity/conclusion mismatch')
    jobs=_gh_json(prefix+'/jobs?per_page=100')
    rows=jobs.get('jobs',[])
    by_name={x.get('name'):x for x in rows}
    insist(jobs.get('total_count')==3 and len(rows)==3 and len(by_name)==3 and
           by_name.get('A07 installed-wheel native debug DAG',{}).get('conclusion')=='success' and
           by_name.get('A05 native DAG + EXO evidence',{}).get('conclusion')=='success' and
           by_name.get('build-debug-apk',{}).get('conclusion')=='skipped' and
           by_name['A07 installed-wheel native debug DAG'].get('run_attempt') in (None,attempt),
           'Unexpected A07/A05/legacy hosted job states')
    steps=by_name['A07 installed-wheel native debug DAG'].get('steps',[])
    required={'Install A06 wheel from immutable Devtool commit',
              'Native build DAG plan and preflight','M16 provision pinned persistent debug signer',
              'Invoke native security to APK to verification DAG',
              'Verify stable M16 debug APK signer',
              'Stage exactly one APK and generate existing M3 and M13 provenance',
              'Record exact native machine receipts and verify host evidence',
              'Upload exact A07 machine evidence',
              'Upload host-qualified debug APK (no device/release qualification)'}
    got={s.get('name'):s.get('conclusion') for s in steps}
    insist(len(steps)==len(got) and all(got.get(n)=='success' for n in required),
           'GitHub job lacks required successful A07 gates')
    listing=_gh_json(prefix+'/artifacts?per_page=100')
    artifacts=listing.get('artifacts',[])
    names={'cinderbox-a07-machine-evidence','cinderbox-a07-debug-apk'}
    selected=[a for a in artifacts if a.get('name') in names]
    insist(len(selected)==2 and {a.get('name') for a in selected}==names and
           all(a.get('expired') is False and
               re.fullmatch('sha256:[0-9a-f]{64}',a.get('digest','')) for a in selected),
           'Missing, duplicated, expired or undigested A07 artifacts')
    with tempfile.TemporaryDirectory(prefix='cinderbox-a07-verify-') as temp:
        root=Path(temp)
        for name in sorted(names):
            where=root/name
            where.mkdir()
            p=subprocess.run(['gh','run','download',str(run_id),'--repo',REPO,
                              '--name',name,'--dir',str(where)],capture_output=True,text=True,timeout=180)
            insist(p.returncode==0,'GitHub download failed for '+name)
        result=verify_local(root/'cinderbox-a07-machine-evidence',
                            root/'cinderbox-a07-debug-apk',sha,run_id,attempt)
    result.update(overall='PASS_CINDERBOX_A07_GITHUB_HOST_RUN_VERIFIED',
                  github_run_qualified=True,
                  artifact_digests={a['name']:a['digest'] for a in selected})
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('source','record','verify-local','verify-run'))
    p.add_argument('--input-dir',type=Path)
    p.add_argument('--evidence-dir',type=Path)
    p.add_argument('--apk-dir',type=Path)
    p.add_argument('--incomplete',action='store_true')
    p.add_argument('--sha',default=os.environ.get('GITHUB_SHA',''))
    p.add_argument('--run-id',type=int,default=int(os.environ.get('GITHUB_RUN_ID','0')))
    p.add_argument('--attempt',type=int,default=int(os.environ.get('GITHUB_RUN_ATTEMPT','0')))
    a=p.parse_args(argv)
    try:
        if a.action=='source':
            source_contract(); print('PASS_CINDERBOX_A07_SOURCE_CONTRACT')
        elif a.action=='record':
            insist(a.input_dir is not None and a.evidence_dir is not None, 'record requires directories')
            print(json.dumps(record(a.input_dir,a.evidence_dir,a.apk_dir,a.incomplete),sort_keys=True))
        elif a.action=='verify-run':
            print(json.dumps(verify_run(a.run_id,a.attempt,a.sha),sort_keys=True))
        else:
            insist(a.input_dir is not None and a.apk_dir is not None, 'verify-local requires both evidence directories')
            print(json.dumps(verify_local(a.input_dir,a.apk_dir,a.sha,a.run_id,a.attempt),sort_keys=True))
        return 0
    except (Refused,OSError,KeyError,ValueError) as exc:
        print('REFUSED_CINDERBOX_A07: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__': raise SystemExit(main())
