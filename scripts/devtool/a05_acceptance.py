#!/usr/bin/env python3
"""A05 native acceptance: source commit, exact overlay scope and focused consumer tests."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[2]
PARENT='ebac91b1deb7da65aa2905e3d75e1825a5ec4097'
FILES={'.devtool.toml','.github/workflows/devtool-android-build.yml',
       'scripts/devtool/a05_actions_qualification.py','scripts/devtool/a05_acceptance.py',
       'scripts/devtool/test_a05_actions_qualification.py',
       'docs/devtool/A05_NATIVE_GITHUB_ACTIONS_QUALIFICATION.md',
       'docs/devtool/DEVTOOL_ADOPTION_IMPROVEMENTS.md'}

def git(*args):
    p=subprocess.run(['git','-c',f'safe.directory={ROOT}','-C',str(ROOT),*args],capture_output=True,text=True)
    if p.returncode:raise RuntimeError('Git state verification failed: '+' '.join(args))
    return p.stdout.strip()

def main():
    try:
        if git('rev-parse','HEAD^')!=PARENT:
            raise RuntimeError('Not the source-pinned A05 commit; expected parent '+PARENT)
        if git('log','-1','--format=%s')!='feat(cinderbox): qualify source-only A05 GitHub DAG':
            raise RuntimeError('Missing native A05 Git commit identity')
        touched=set(git('diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines())
        if touched!=FILES:raise RuntimeError('Commit scope differs from seven reviewed A05 files: '+repr(sorted(touched)))
        if git('status','--porcelain','--untracked-files=all'):
            raise RuntimeError('Worktree must be clean for native acceptance')
        cmd=[sys.executable,'-m','unittest','discover','-s','scripts/devtool','-p','test_a05_*.py','-q']
        env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
        tests=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
        if tests.returncode:raise RuntimeError('A05 qualification tests failed:\n'+tests.stdout+'\n'+tests.stderr)
        import re
        counts=re.findall(r'Ran (\d+) tests?',tests.stderr)
        passed=int(counts[-1]) if counts else 0
        if passed<19:raise RuntimeError('Insufficient A05 regression test count')
        for command in ([sys.executable,'scripts/devtool/a05_actions_qualification.py','source'],
                        [sys.executable,'scripts/devtool/check_security_contract.py'],
                        [sys.executable,'scripts/devtool/m24_verify_ux_gate.py']):
            p=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True)
            if p.returncode:raise RuntimeError('A05 source prerequisite failed: '+repr(command)+' '+p.stderr[-500:])
        now=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        out=Path.home()/'.local/state/cinderbox/a05'/('acceptance-'+now+'.json')
        out.parent.mkdir(parents=True,exist_ok=True)
        receipt={'overall':'PASS_CINDERBOX_A05_LOCAL_ACCEPTANCE','pytest_passed':passed,
                 'pytest_skipped':0,'source_commit':git('rev-parse','HEAD'),
                 'source_parent':PARENT,'touched_files':sorted(touched),'github_run_qualified':False,
                 'android_device_qualified':False,'release_qualified':False,'receipt':str(out)}
        out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
        print(json.dumps(receipt,sort_keys=True));return 0
    except (OSError,RuntimeError,ValueError) as e:
        print('CINDERBOX_A05_ACCEPTANCE_REFUSED:',e,file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
