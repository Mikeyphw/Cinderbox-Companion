#!/usr/bin/env python3
"""Source-pinned targeted Cinderbox CI and periodic/manual full gate.

No local Gradle, no automatic merge/release, no live Nexus test.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

INITIAL_BASELINE = '0314a34ba9ce42c11c7ab09978a6cdc2ad6a6274'
TAG_PREFIX = 'cinderbox-full-gate/'
DEFAULT_INTERVAL = 5
# Exact canonical workflows, not the dozens of historical presentation jobs.
REQUIRED = {
    'build.yml': {'build'},
    'cbnx01-firefox-handoff.yml': {'source-and-jvm', 'api36-nxm-policy'},
    'cbnx02-download-ux.yml': {'source-and-build', 'hosted-api36'},
    'nex-r5-unified-details.yml': {'source-contract', 'api36-unified-details', 'community-schema-probe'},
    'r47-ui-acceptance.yml': {'host-source', 'emulator-ui'},
    'r48-real-activity-acceptance.yml': {'host-source', 'emulator-real-activity'},
}
GROUP_SCRIPTS = {
    'downloads': ['cbnx01_gate.py', 'cbnx02_source_gate.py', 'ux08a_gate.py'],
    'nexus': ['nex_r5_gate.py', 'ux05bd_gate.py', 'cbnx01_gate.py'],
    'ui': ['ux08a_gate.py', 'r47_gate.py'],
    'mods': ['m25_profile_gate.py', 'cbnx02_source_gate.py'],
    'storage': ['r43c_gate.py', 'r43d_gate.py'],
}
GROUP_TESTS = {
    'downloads': ['test_cbnx01_nxm_ingress.py', 'test_ux08a_gate.py'],
    'nexus': ['test_nex_r5_gate.py', 'test_cbnx01_nxm_ingress.py'],
    'ui': ['test_ux08a_gate.py', 'test_r47_gate.py'],
    'mods': ['test_m25_profile_gate.py'],
    'storage': ['test_r43c_gate.py'],
}
SENSITIVE_PATHS = ('.github/workflows/', 'scripts/ci/', 'scripts/devtool/ci_workflow_contract.py',
                   'scripts/devtool/test_a10_lane_consolidation.py')
IMMEDIATE_RISK = ('docs/security/M3_RELEASE_POLICY.json', 'app/src/main/AndroidManifest.xml',
                  'gradle/wrapper/', 'app/build.gradle.kts', 'app/src/main/java/com/sdvsync/local/StoragePreflight.kt')


def git(*args: str, cwd: Path | None = None) -> str:
    p = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError('CBNX_CI_GIT_REFUSED:' + ' '.join(args) + ':' + p.stderr.strip()[:300])
    return p.stdout.strip()


def paths_between(base: str, head: str, cwd: Path | None = None) -> list[str]:
    for sha in (base, head):
        if not re.fullmatch(r'[0-9a-f]{40}', sha):
            raise ValueError('CBNX_CI_INVALID_SHA')
    data = subprocess.run(['git', 'diff', '--name-only', '-z', '--no-renames',
                           '--diff-filter=ACDMRTUXB', base, head], cwd=cwd, capture_output=True)
    if data.returncode:
        raise RuntimeError('CBNX_CI_DIFF_REFUSED:' + data.stderr.decode(errors='replace')[:300])
    return sorted({s.decode('utf-8') for s in data.stdout.split(b'\0') if s})


def classify(paths: list[str]) -> dict:
    groups: set[str] = set()
    sensitive = False
    android = False
    for p in paths:
        low = p.lower()
        if p.startswith('docs/') and p != 'docs/security/M3_RELEASE_POLICY.json':
            continue
        if any(p.startswith(x) for x in SENSITIVE_PATHS):
            sensitive = True
        if p.startswith(('app/', 'gradle/')) or p in ('settings.gradle.kts', 'build.gradle.kts', 'gradle.properties'):
            android = True
        if ('/moddownload' in low or 'cbnx0' in low or '/mods/api/nxm' in low
                or 'moddownloads' in low or '/mods/modsafety' in low):
            groups.add('downloads')
        if ('nexus' in low or 'nex_r' in low or 'moddetail' in low or 'htmltext' in low):
            groups.add('nexus')
        if p.startswith(('app/src/main/java/com/sdvsync/ui/', 'app/src/androidTest/java/com/sdvsync/ui/')) or 'ux0' in low:
            groups.add('ui')
        if p.startswith(('app/src/main/java/com/sdvsync/mods/', 'app/src/test/java/com/sdvsync/mods/')) or 'm25_' in low:
            groups.add('mods')
        if p.startswith(('app/src/main/java/com/sdvsync/local/', 'app/src/main/java/com/sdvsync/download/')) or 'r43' in low:
            groups.add('storage')
    if sensitive or (android and not groups):
        groups.update(GROUP_SCRIPTS)
    scripts = sorted({file for group in groups for file in GROUP_SCRIPTS[group]})
    tests = sorted({file for group in groups for file in GROUP_TESTS[group]})
    return {'groups': sorted(groups) or ['baseline'], 'source_gates': scripts,
            'source_tests': tests, 'needs_android': android, 'ci_sensitive': sensitive,
            'changed_files': len(paths)}


def run_targeted(plan: dict, root: Path) -> None:
    policy_path = root / 'docs/security/M3_RELEASE_POLICY.json'
    policy = json.loads(policy_path.read_text(encoding='utf-8'))
    for key in ('release_enabled', 'publication_enabled', 'automatic_device_install', 'device_qualification_complete'):
        if policy.get(key) is not False:
            raise RuntimeError('CBNX_CI_UNSAFE_RELEASE_POLICY:' + key)
    subprocess.run([sys.executable, '-B', 'scripts/devtool/check_security_contract.py'], cwd=root, check=True)
    subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts/ci',
                    '-p', 'test_cinderbox_ci_policy.py', '-v'], cwd=root, check=True)
    for file in plan['source_gates']:
        target = root / 'scripts/devtool' / file
        if not target.is_file() or target.is_symlink():
            raise RuntimeError('CBNX_CI_MISSING_SOURCE_GATE:' + file)
        print('CBNX_CI_SOURCE_GATE: ' + file, flush=True)
        subprocess.run([sys.executable, '-B', str(target)], cwd=root, check=True)
    for file in plan['source_tests']:
        target = root / 'scripts/devtool' / file
        if not target.is_file() or target.is_symlink():
            raise RuntimeError('CBNX_CI_MISSING_SOURCE_TEST:' + file)
        subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts/devtool',
                        '-p', file, '-v'], cwd=root, check=True)
    print('CBNX_CI_TARGETED_SOURCE_PASS groups=' + ','.join(plan['groups']), flush=True)


def first_parent(head: str, cwd: Path | None = None) -> list[str]:
    return git('rev-list', '--first-parent', head, cwd=cwd).splitlines()


def last_gate(head: str, cwd: Path | None = None) -> tuple[str, str]:
    history = first_parent(head, cwd=cwd)
    indices = {sha: i for i, sha in enumerate(history)}
    tags = git('tag', '--list', TAG_PREFIX + '*', cwd=cwd).splitlines()
    match: list[tuple[int, str, str]] = []
    for tag in tags:
        sha = git('rev-parse', f'refs/tags/{tag}^{{commit}}', cwd=cwd)
        if sha in indices:
            match.append((indices[sha], sha, tag))
    if match:
        _, sha, tag = min(match)
        return sha, tag
    if INITIAL_BASELINE not in indices:
        raise RuntimeError('CBNX_CI_GATE_BASELINE_NOT_ANCESTOR')
    return INITIAL_BASELINE, 'initial-counting-anchor-uncertified'


def gate_plan(head: str, interval: int = DEFAULT_INTERVAL, force: bool = False,
              cwd: Path | None = None) -> dict:
    if not 1 <= interval <= 25:
        raise ValueError('CBNX_CI_BAD_GATE_INTERVAL')
    history = first_parent(head, cwd=cwd)
    anchor, tag = last_gate(head, cwd=cwd)
    units = history.index(anchor)
    changes = paths_between(anchor, head, cwd=cwd)
    risks = [p for p in changes if any(p.startswith(r) for r in IMMEDIATE_RISK)]
    reasons = (['manual'] if force else []) + (['cadence'] if units >= interval else []) + (
        ['security-sensitive'] if risks else [])
    return {'head_sha': head, 'baseline_sha': anchor, 'baseline_tag': tag,
            'first_parent_units': units, 'interval': interval,
            'high_risk_paths': risks, 'due': bool(reasons), 'reasons': reasons}


def api(method: str, path: str, payload: dict | None = None) -> dict | None:
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    if not token or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise RuntimeError('CBNX_CI_MISSING_ACTIONS_AUTH')
    url = f'https://api.github.com/repos/{repo}/{path}'
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'cinderbox-ci-router'}
    try:
        with urlopen(Request(url, data=data, headers=headers, method=method), timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except HTTPError as err:
        raise RuntimeError(f'CBNX_CI_GITHUB_API_{err.code}:{method} {path}') from err


def ensure_exact_master(head: str) -> None:
    if os.environ.get('GITHUB_REF') != 'refs/heads/master':
        raise RuntimeError('CBNX_CI_GATE_MASTER_ONLY')
    info = api('GET', 'branches/master')
    if not info or info['commit']['sha'] != head:
        raise RuntimeError('CBNX_CI_GATE_MASTER_MOVED')


def dispatched_runs(file: str, head: str) -> list[dict]:
    response = api('GET', f'actions/workflows/{file}/runs?branch=master&event=workflow_dispatch&per_page=100')
    if response is None:
        raise RuntimeError('CBNX_CI_GATE_RUN_LIST_MISSING:' + file)
    matching = [run for run in response.get('workflow_runs', [])
                if run.get('head_sha') == head and run.get('event') == 'workflow_dispatch']
    if response.get('total_count', 0) > 100 and not matching:
        raise RuntimeError('CBNX_CI_GATE_RUN_LIST_INCOMPLETE:' + file)
    return matching


def verify_run(file: str, run: dict, head: str) -> None:
    if run.get('head_sha') != head or run.get('status') != 'completed' or run.get('conclusion') != 'success':
        raise RuntimeError('CBNX_CI_GATE_RUN_NOT_GREEN:' + file)
    response = api('GET', f'actions/runs/{run["id"]}/jobs?filter=latest&per_page=100')
    if not response or response.get('total_count', 0) > 100:
        raise RuntimeError('CBNX_CI_GATE_JOB_LIST_INCOMPLETE:' + file)
    jobs = {job['name']: job for job in response.get('jobs', [])}
    expected = REQUIRED[file]
    if not expected <= jobs.keys():
        raise RuntimeError('CBNX_CI_GATE_MISSING_JOBS:' + file)
    for name in expected:
        job = jobs[name]
        if (job.get('conclusion') != 'success' or job.get('status') != 'completed'
                or job.get('head_sha') != head):
            raise RuntimeError('CBNX_CI_GATE_JOB_REFUSED:' + file + ':' + name)
    print(f'CBNX_CI_FULL_GATE_WORKFLOW_PASS file={file} run={run["id"]} jobs={len(expected)}', flush=True)


def dispatch_full_gate(head: str, interval: int, force: bool) -> None:
    ensure_exact_master(head)
    plan = gate_plan(head, interval, force)
    print('CBNX_CI_GATE_PLAN: ' + json.dumps(plan, sort_keys=True), flush=True)
    if not plan['due']:
        print('CBNX_CI_GATE_NOT_DUE', flush=True)
        return
    known = {name: {x['id'] for x in dispatched_runs(name, head)} for name in REQUIRED}
    for file in REQUIRED:
        ensure_exact_master(head)
        api('POST', f'actions/workflows/{file}/dispatches', {'ref': 'master'})
        print('CBNX_CI_GATE_DISPATCHED:' + file, flush=True)
    pending = set(REQUIRED)
    deadline = time.monotonic() + 110 * 60
    while pending and time.monotonic() < deadline:
        ensure_exact_master(head)
        for file in sorted(pending):
            new = [r for r in dispatched_runs(file, head) if r['id'] not in known[file]]
            if not new:
                continue
            run = max(new, key=lambda x: x['id'])
            if run['status'] != 'completed':
                continue
            verify_run(file, run, head)
            pending.remove(file)
        if pending:
            print('CBNX_CI_GATE_WAIT:' + ','.join(sorted(pending)), flush=True)
            time.sleep(20)
    if pending:
        raise RuntimeError('CBNX_CI_GATE_TIMEOUT:' + ','.join(sorted(pending)))
    ensure_exact_master(head)
    tag = TAG_PREFIX + os.environ['GITHUB_RUN_ID']
    api('POST', 'git/refs', {'ref': 'refs/tags/' + tag, 'sha': head})
    print(f'CBNX_CI_FULL_GATE_TAGGED_PASS tag={tag} sha={head}', flush=True)


def main() -> None:
    cli = argparse.ArgumentParser()
    sub = cli.add_subparsers(dest='command', required=True)
    for command in ('classify', 'run-targeted'):
        p = sub.add_parser(command)
        p.add_argument('--base', required=True)
        p.add_argument('--head', required=True)
        if command == 'classify':
            p.add_argument('--github-output')
    for command in ('gate-plan', 'gate-dispatch'):
        p = sub.add_parser(command)
        p.add_argument('--head', required=True)
        p.add_argument('--interval', type=int, default=DEFAULT_INTERVAL)
        p.add_argument('--force', action='store_true')
        if command == 'gate-plan':
            p.add_argument('--github-output')
    args = cli.parse_args()
    root = Path.cwd()
    if args.command in ('classify', 'run-targeted'):
        plan = classify(paths_between(args.base, args.head, root))
        print('CBNX_CI_TARGETED_PLAN: ' + json.dumps(plan, sort_keys=True), flush=True)
        if args.command == 'classify' and args.github_output:
            with open(args.github_output, 'a', encoding='utf-8') as out:
                out.write(f"needs_android={str(plan['needs_android']).lower()}\n")
                out.write(f"groups={','.join(plan['groups'])}\n")
                out.write(f"head_sha={args.head}\nbase_sha={args.base}\n")
        elif args.command == 'run-targeted':
            run_targeted(plan, root)
    elif args.command == 'gate-plan':
        plan = gate_plan(args.head, args.interval, args.force, root)
        print('CBNX_CI_GATE_PLAN: ' + json.dumps(plan, sort_keys=True))
        if args.github_output:
            with open(args.github_output, 'a', encoding='utf-8') as out:
                out.write(f"due={str(plan['due']).lower()}\n")
                out.write(f"first_parent_units={plan['first_parent_units']}\n")
    else:
        dispatch_full_gate(args.head, args.interval, args.force)

if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as err:
        print(str(err), file=sys.stderr)
        sys.exit(1)
