#!/usr/bin/env python3
"""A05-R1 native acceptance: verify exact hotfix commit and selected source tests."""
from __future__ import annotations
from datetime import datetime,timezone
import json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PARENT='b7559c0277f34e3ada9638ef605b6af68ec658ee'
MESSAGE='fix(cinderbox): run A05 DAG from pinned Devtool source checkout'
FILES={'.github/workflows/devtool-android-build.yml','scripts/devtool/a05_actions_qualification.py',
 'scripts/devtool/test_a05_r1_source_runtime.py','scripts/devtool/a05_r1_acceptance.py',
 'docs/devtool/A05_NATIVE_GITHUB_ACTIONS_QUALIFICATION.md','docs/devtool/DEVTOOL_ADOPTION_IMPROVEMENTS.md'}
def git(*args):
 p=subprocess.run(['git','-c',f'safe.directory={ROOT}','-C',str(ROOT),*args],capture_output=True,text=True,timeout=15)
 if p.returncode:raise RuntimeError('Git check failed: '+' '.join(args))
 return p.stdout.strip()
def main():
 try:
  if git('rev-parse','HEAD^')!=PARENT:raise RuntimeError('Unexpected source parent')
  if git('log','-1','--format=%s')!=MESSAGE:raise RuntimeError('Commit subject differs')
  if set(git('diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines())!=FILES:
   raise RuntimeError('Hotfix commit file scope differs')
  if git('status','--porcelain','--untracked-files=all'):raise RuntimeError('Worktree not clean')
  env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
  cmd=[sys.executable,'-m','unittest','discover','-s','scripts/devtool','-p','test_a05_*.py','-q']
  p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=180)
  if p.returncode:raise RuntimeError('Regressions failed: '+p.stdout[-2000:]+p.stderr[-2000:])
  counts=re.findall(r'Ran (\d+) tests?',p.stderr);number=int(counts[-1]) if counts else 0
  if number<26:raise RuntimeError('Too few A05 tests: '+str(number))
  for args in ([sys.executable,'scripts/devtool/a05_actions_qualification.py','source'],
               [sys.executable,'scripts/devtool/check_security_contract.py'],
               [sys.executable,'scripts/devtool/m24_verify_ux_gate.py']):
   p=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
   if p.returncode:raise RuntimeError('Source prerequisite failed: '+repr(args)+p.stderr[-1000:])
  now=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
  path=Path.home()/'.local/state/cinderbox/a05-r1'/('acceptance-'+now+'.json');path.parent.mkdir(parents=True,exist_ok=True)
  obj={'overall':'PASS_CINDERBOX_A05_R1_LOCAL_ACCEPTANCE','pytest_passed':number,'pytest_skipped':0,
       'source_commit':git('rev-parse','HEAD'),'source_parent':PARENT,'touched_files':sorted(FILES),
       'github_run_qualified':False,'release_qualified':False,'android_device_qualified':False,'receipt':str(path)}
  path.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n');print(json.dumps(obj,sort_keys=True));return 0
 except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as e:
  print('CINDERBOX_A05_R1_ACCEPTANCE_REFUSED:',e,file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
