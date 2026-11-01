#!/usr/bin/env python3
"""Source-bound, current-branch Devtool Actions debug-APK command-line bridge.

Run: python3 -B scripts/devtool/hosted_debug.py plan
     python3 -B scripts/devtool/hosted_debug.py run --yes
     python3 -B scripts/devtool/hosted_debug.py watch --request-id <32-hex-id>
     python3 -B scripts/devtool/hosted_debug.py artifacts --request-id <32-hex-id>

Uses Devtool's native Actions API, not a legacy wrapper config that the
A05/A07 pinned releases cannot parse. No local Gradle/build ever runs here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
REPO = 'Mikeyphw/Cinderbox-Companion'
WORKFLOW = 'devtool-android-build.yml'
INPUTS = ('project_dir=.', 'module=app', 'variant=debug', 'format=apk',
          'a07_native_build=true', 'a05_mode=native-only')
BRANCH = re.compile(r'[A-Za-z0-9][A-Za-z0-9/_.-]{0,199}\Z')
REQUEST = re.compile(r'[0-9a-f]{32}\Z')


def output(*argv: str) -> str:
    proc = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=False)
    if proc.returncode:
        raise RuntimeError(f'Command failed ({proc.returncode}): {argv[0]} {argv[1] if len(argv)>1 else ""}: '
                           + (proc.stderr or proc.stdout).strip()[:600])
    return proc.stdout.strip()


def source_identity() -> tuple[str, str]:
    branch = output('git', 'symbolic-ref', '--quiet', '--short', 'HEAD')
    if (not BRANCH.fullmatch(branch) or '..' in branch or branch.startswith('-') or
        branch.endswith('/') or '/.' in branch or '@{' in branch):
        raise RuntimeError('Unsafe or detached Git branch')
    # This dispatch is bound to the exact tree under review, not arbitrary
    # dirty files or a remote branch whose SHA has advanced.
    if output('git', 'status', '--porcelain', '--untracked-files=normal'):
        raise RuntimeError('Working tree is not clean; commit/push first')
    head = output('git', 'rev-parse', '--verify', 'HEAD')
    if not re.fullmatch('[0-9a-f]{40}', head):
        raise RuntimeError('Invalid local Git source SHA')
    remote_url = f'repos/{REPO}/git/ref/heads/{quote(branch, safe="/")}'
    data = json.loads(output('gh', 'api', remote_url))
    remote = data.get('object', {}).get('sha')
    if remote != head:
        raise RuntimeError(f'Branch {branch} differs from GitHub: local {head}, remote {remote}; push first')
    return branch, head


def make_command(operation: str, *, branch: str = '', request_id: str = '') -> list[str]:
    base = ['devtool', '--repo', str(ROOT), 'actions']
    if operation in {'plan', 'run'}:
        if not BRANCH.fullmatch(branch):
            raise ValueError('Invalid build branch')
        command = base + [operation, WORKFLOW, '--github-repo', REPO, '--ref', branch]
        for item in INPUTS:
            command += ['--input', item]
        if operation == 'run':
            command += ['--yes']
        return command + ['--json']
    if operation in {'watch', 'artifacts'}:
        if not REQUEST.fullmatch(request_id):
            raise ValueError('Invalid Devtool request ID; expected 32 lowercase hex characters')
        return base + [operation, '--request-id', request_id, '--json']
    raise ValueError('Unknown operation')


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=('plan','run','watch','artifacts'))
    p.add_argument('--yes', action='store_true', help='Explicitly approve remote build dispatch')
    p.add_argument('--request-id', default='', help='32-hex Devtool dispatch request ID')
    args = p.parse_args(argv)
    if args.operation == 'run' and not args.yes:
        p.error('run requires explicit --yes')
    if args.yes and args.operation != 'run':
        p.error('--yes is valid only for run')
    if args.operation in ('watch','artifacts') and not REQUEST.fullmatch(args.request_id):
        p.error('watch/artifacts require a 32-character lowercase hex --request-id')
    if args.request_id and args.operation not in ('watch','artifacts'):
        p.error('--request-id is not valid for plan/run')
    try:
        branch, sha = source_identity() if args.operation in ('plan','run') else ('','')
        if sha:
            print(f'Verified Cinderbox {branch} at exact local/remote SHA {sha}', file=sys.stderr)
        command = make_command(args.operation,branch=branch,request_id=args.request_id)
        return subprocess.run(command, cwd=ROOT, check=False).returncode
    except (RuntimeError, ValueError, json.JSONDecodeError, OSError) as exc:
        print('REFUSED_HOSTED_DEBUG: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
