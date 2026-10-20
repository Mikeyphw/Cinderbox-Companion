#!/usr/bin/env python3
"""A07 exact-commit source acceptance; never dispatches GitHub or touches a device."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

PARENT='e9a5fd363ba4af3a3ce95e71de2c9c230e5691b0'
BRANCH='feature/m24-steam-download-safety'
PATHS=('.github/workflows/devtool-android-build.yml',
       'docs/devtool/DEVTOOL_ADOPTION_IMPROVEMENTS.md',
       'docs/devtool/A07_INSTALLED_WHEEL_NATIVE_DEBUG.md',
       'scripts/devtool/m3_build_evidence.py',
       'scripts/devtool/a07_native_debug.py',
       'scripts/devtool/a07_acceptance.py',
       'scripts/devtool/test_a07_native_debug.py')

def call(root,*args):
    p=subprocess.run(['git','-c',f'safe.directory={root}','-C',str(root),*args],capture_output=True,text=True,timeout=20)
    if p.returncode:raise ValueError('Git command failed: '+' '.join(args))
    return p.stdout.strip()

def run(root,argv):
    p=subprocess.run(argv,cwd=root,capture_output=True,text=True,timeout=90)
    if p.returncode:raise ValueError('Validation failed: '+' '.join(argv)+'\n'+p.stdout[-1500:]+p.stderr[-1000:])
    return p.stdout+p.stderr

def main():
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument('--repo',type=Path,required=True)
    a=pa.parse_args();root=a.repo.expanduser().resolve()
    try:
        head=call(root,'rev-parse','HEAD')
        if call(root,'rev-parse','HEAD^')!=PARENT or call(root,'branch','--show-current')!=BRANCH:
            raise ValueError('A07 must be an exact child of the reviewed A05-R2 commit on the expected branch')
        if call(root,'status','--porcelain','--untracked-files=all'):
            raise ValueError('A07 worktree must be clean')
        paths=call(root,'diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines()
        if sorted(paths)!=sorted(PATHS):raise ValueError('A07 commit scope drift')
        hashes={}
        for rel in PATHS:
            f=root/rel
            if not f.is_file() or f.is_symlink():raise ValueError('Missing/unsafe path '+rel)
            saved=subprocess.run(['git','-C',str(root),'show','HEAD:'+rel],capture_output=True,timeout=15)
            if saved.returncode or saved.stdout!=f.read_bytes():raise ValueError('Source differs from commit '+rel)
            hashes[rel]=hashlib.sha256(f.read_bytes()).hexdigest()
        ledger='docs/devtool/DEVTOOL_ADOPTION_IMPROVEMENTS.md'
        orig=subprocess.run(['git','-C',str(root),'show','HEAD^:'+ledger],capture_output=True,check=True).stdout
        if not (root/ledger).read_bytes().startswith(orig):raise ValueError('Cumulative improvements ledger rewritten')
        run(root,[sys.executable,'scripts/devtool/a07_native_debug.py','source'])
        tests=run(root,[sys.executable,'-m','unittest','discover','-s','scripts/devtool','-p','test_a07_native_debug.py','-v'])
        if 'Ran 9 tests' not in tests or '\nOK' not in tests:raise ValueError('Nine deterministic A07 regressions required')
        run(root,[sys.executable,'scripts/devtool/m3_build_evidence.py','source'])
        run(root,[sys.executable,'scripts/devtool/a05_actions_qualification.py','source'])
        stamp=datetime.now(timezone.utc)
        rec={'schema_version':1,'producer':'cinderbox-a07-local-acceptance',
             'overall':'PASS_CINDERBOX_A07_LOCAL_SOURCE_ACCEPTANCE',
             'source_commit':head,'source_parent':PARENT,'source_tree':call(root,'rev-parse','HEAD^{tree}'),
             'source_sha256':hashes,'unittest_passed':9,'unittest_skipped':0,
             'm3_source_pass':True,'a05_source_preserved':True,
             'github_run_qualified':False,'android_device_qualified':False,
             'release_qualified':False,'timestamp_utc':stamp.isoformat()}
        dest=Path.home()/'.local/state/cinderbox/a07'
        dest.mkdir(parents=True,exist_ok=True)
        f=dest/('acceptance-'+stamp.strftime('%Y%m%dT%H%M%S%fZ')+'.json')
        fd=os.open(f,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as h:json.dump(rec,h,indent=2,sort_keys=True);h.write('\n')
        print(json.dumps({'overall':rec['overall'],'source_commit':head,
                          'unittest_passed':9,'receipt':str(f),
                          'github_run_qualified':False},sort_keys=True))
        return 0
    except (ValueError,OSError,subprocess.CalledProcessError,subprocess.TimeoutExpired) as exc:
        print('REFUSED_CINDERBOX_A07_LOCAL_ACCEPTANCE:',str(exc),file=sys.stderr)
        return 2
if __name__=='__main__':raise SystemExit(main())
