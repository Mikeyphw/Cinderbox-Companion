#!/usr/bin/env python3
"""A05-R2 native acceptance, source-bound and explicitly NOT remote qualification."""
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
PARENT='7675f3471326b3ca52a9474a17d96a6bde2943d6'
MESSAGE='fix(cinderbox): verify A05 DAG run without GitHub inputs metadata'
FILES={
  'scripts/devtool/a05_actions_qualification.py',
  'scripts/devtool/test_a05_r2_remote_proof.py',
  'scripts/devtool/a05_r2_acceptance.py',
  'docs/devtool/A05_NATIVE_GITHUB_ACTIONS_QUALIFICATION.md',
  'docs/devtool/DEVTOOL_ADOPTION_IMPROVEMENTS.md',
}

def git(*args):
    p=subprocess.run(['git','-c',f'safe.directory={ROOT}','-C',str(ROOT),*args],
                     capture_output=True,text=True,timeout=20)
    if p.returncode:raise RuntimeError('Git check failed: '+' '.join(args))
    return p.stdout.strip()

def main():
    try:
        if git('rev-parse','HEAD^')!=PARENT:raise RuntimeError('A05-R2 parent source is not exact accepted A05-R1 commit')
        if git('log','-1','--format=%s')!=MESSAGE:raise RuntimeError('Expected native hotfix auto-commit')
        if set(git('diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines())!=FILES:
            raise RuntimeError('Unexpected commit scope')
        if git('status','--porcelain','--untracked-files=all'):raise RuntimeError('Dirty worktree')
        env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
        p=subprocess.run([sys.executable,'-m','unittest','discover','-s','scripts/devtool',
                          '-p','test_a05_*.py','-q'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=180)
        if p.returncode:raise RuntimeError('A05 tests failed: '+p.stderr[-2200:])
        tests=[int(n) for n in re.findall(r'Ran (\d+) tests?',p.stderr)]
        count=tests[-1] if tests else 0
        if count<32:raise RuntimeError('Expected >= 32 A05 checks, got '+str(count))
        for args in ([sys.executable,'scripts/devtool/a05_actions_qualification.py','source'],
                     [sys.executable,'scripts/devtool/check_security_contract.py'],
                     [sys.executable,'scripts/devtool/m24_verify_ux_gate.py']):
            p=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=40)
            if p.returncode:raise RuntimeError('Source gate failed: '+repr(args)+p.stderr[-1200:])
        now=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        receipt=Path.home()/'.local/state/cinderbox/a05-r2'/('acceptance-'+now+'.json')
        receipt.parent.mkdir(parents=True,exist_ok=True)
        obj={'overall':'PASS_CINDERBOX_A05_R2_LOCAL_ACCEPTANCE','pytest_passed':count,
             'pytest_skipped':0,'source_commit':git('rev-parse','HEAD'),
             'source_parent':PARENT,'touched_files':sorted(FILES),
             'github_run_qualified':False,'release_qualified':False,
             'android_device_qualified':False,'receipt':str(receipt)}
        receipt.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
        print(json.dumps(obj,sort_keys=True));return 0
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as e:
        print('CINDERBOX_A05_R2_ACCEPTANCE_REFUSED:',e,file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
