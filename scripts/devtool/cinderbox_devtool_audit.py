#!/usr/bin/env python3
"""Offline Cinderbox Devtool consumer contract audit (no Gradle or network).

This checks configuration ownership/invariants; it is NOT a native Devtool
parser/preflight and does not qualify a hosted APK, signer or device.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
CHECKSUM = 'f397b287023acdba1e9f6fc5ea72d22dd63669d59ed4a289a29b1a76eee151c6'
WORKFLOW = 'devtool-android-build.yml'
HOST = {'storage-alias-source','devtool-contract','security-contract','a05-source-regression',
        'a07-source-regression','a10-source-regression'}
PINS = {
    'A05_DEVTOOL_SHA': '08eb13991b5d1c623b64fdd8f9524418ee27207e',
    'A07_DEVTOOL_SHA': '409c5527532eaa1ee62b8111e030732d3f9e2791',
}
NODE24_ACTIONS = (
    'actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09',
    'actions/setup-java@b6effb05e454b25005698d916606bdc6ffcbf961',
    'android-actions/setup-android@be39fa834029ff78f1a44aa3bb0819b8fc2bd8fd',
    'gradle/actions/setup-gradle@0723195856401067f7a2779048b490ace7a47d7c',
    'actions/upload-artifact@330a01c490aca151604b8cf639adc76d48f6c5d4',
)



def audit(root: Path) -> dict:
    root = root.resolve()
    issues: list[str] = []
    def require(ok: bool, code: str) -> None:
        if not ok:
            issues.append(code)

    try:
        data = (root / '.devtool.toml').read_bytes()
        config = tomllib.loads(data.decode('utf-8'))
    except (FileNotFoundError, ValueError, UnicodeError) as exc:
        return {'schema_version': 1, 'ok': False, 'issues': [f'CONFIG_PARSE: {exc}']}
    target = config.get('targets', {}).get('cinderbox', {})
    jobs = target.get('jobs', {})
    flows = target.get('workflows', {})
    wrapper = config.get('wrapper', {})
    cmds = wrapper.get('commands', {})
    require(wrapper.get('schema') == 2, 'WRAPPER_SCHEMA_2_REQUIRED')
    require(wrapper.get('default_command') == 'host-check', 'UNSAFE_WRAPPER_DEFAULT')
    require(config.get('workspace', {}).get('default_target') == 'cinderbox', 'TARGET_DEFAULT_MISMATCH')
    policy = config.get('workspace', {}).get('scheduler', {})
    require(policy.get('parallel') is True and policy.get('max_gradle_nodes') == 1
            and 1 <= policy.get('max_parallel_nodes', 0) <= 4, 'SCHEDULER_POLICY_MISMATCH')
    require(target.get('runner') == 'android', 'ANDROID_RUNNER_REQUIRED')
    require(jobs.get('connected-tests',{}).get('metadata',{}).get('explicit_only') is True,
            'DEVICE_MUST_REMAIN_EXPLICIT_ONLY')
    require(set(HOST) <= set(jobs), 'MISSING_HOST_JOBS')
    host_flow = flows.get('host-check', [])
    require(len(host_flow) == len(HOST), 'HOST_GRAPH_NODE_COUNT')
    host_refs: set[str] = set()
    graph_counts = {}
    for name, steps in flows.items():
        if not isinstance(steps, list) or not steps:
            issues.append('EMPTY_WORKFLOW:' + name)
            continue
        ids: set[str] = set()
        edges: dict[str,list[str]] = {}
        for row in steps:
            if isinstance(row, str):
                ref = row
            elif isinstance(row, dict):
                ref = row.get('ref', '')
                ident = row.get('id', '')
                if not ident or ident in ids:
                    issues.append('NONUNIQUE_NODE_ID:' + name)
                ids.add(ident)
                edges[ident] = list(row.get('depends_on', []))
            else:
                issues.append('UNKNOWN_STEP_TYPE:' + name)
                continue
            if not isinstance(ref, str) or not ref.startswith('job:'):
                issues.append('NONLOCAL_JOB:' + name)
                continue
            local = ref[4:]
            if local not in jobs:
                issues.append('UNKNOWN_JOB:' + name + ':' + local)
            if name == 'host-check':
                host_refs.add(local)
                if (local not in HOST or jobs.get(local,{}).get('runner') != 'command' or
                    jobs.get(local,{}).get('metadata',{}).get('read_only') is not True or
                    jobs.get(local,{}).get('execution_environment') != 'native'):
                    issues.append('UNSAFE_HOST_JOB:' + local)
                job = jobs.get(local, {})
                argv = job.get('command', [])
                # A07 signs a source contract around its original security argv;
                # enforce no bytecode writes via environment without changing it.
                no_bytecode = (isinstance(argv, list) and len(argv) >= 2 and
                    (argv[1] == '-B' or
                     (local == 'security-contract' and
                      job.get('env', {}).get('PYTHONDONTWRITEBYTECODE') == '1')))
                if (not no_bytecode or not isinstance(argv, list) or argv[0] != 'python3' or
                    (local == 'security-contract' and argv != ['python3','scripts/devtool/check_security_contract.py']) or
                    any('gradle' in str(arg).lower() or 'sh -c' in str(arg).lower() for arg in argv)):
                    issues.append('HOST_JOB_NOT_PYTHON_ONLY:' + local)
        for ident, deps in edges.items():
            if any(dep not in ids or dep == ident for dep in deps):
                issues.append('INVALID_DAG_DEPENDENCY:' + name + ':' + ident)
        def visit(n: str, stack: set[str], done: set[str]) -> None:
            if n in stack:
                issues.append('DAG_CYCLE:' + name)
                return
            if n in done: return
            stack.add(n)
            for dep in edges.get(n,[]):
                if dep in edges: visit(dep, stack, done)
            stack.remove(n); done.add(n)
        done: set[str] = set()
        for ident in edges: visit(ident,set(),done)
        graph_counts[name] = len(steps)
    require(host_refs == HOST, 'HOST_GRAPH_REFERENCES')
    require(all(not (row.get('gradle_tasks') or row.get('action')) for name,row in jobs.items() if name in HOST),
            'HOST_GRADLE_ACTION_FORBIDDEN')
    require(all((v.get('workflow') in flows if 'workflow' in v else True)
                for v in cmds.values()), 'BROKEN_WRAPPER_WORKFLOW')
    require(cmds.get('host-check',{}).get('workflow') == 'host-check', 'HOST_WRAPPER_MISMATCH')
    # Native A05/A07 wheels predate typed `actions` wrappers. The whole
    # config must load on *both* releases, not just the local latest Devtool.
    for name, command in cmds.items():
        require(not command.get('actions') and command.get('devtool') != 'actions',
                'PINNED_DEVTOOL_INCOMPATIBLE_WRAPPER:' + name)
    require(not any(name.startswith('ci-debug-') for name in cmds),
            'REMOTE_WRAPPER_MUST_BE_EXTERNAL')
    hosted = root / 'scripts/devtool/hosted_debug.py'
    require(hosted.is_file(), 'MISSING_BRANCH_AWARE_DISPATCH_HELPER')
    try:
        flow_text = (root / '.github/workflows' / WORKFLOW).read_text()
        for k,v in PINS.items():
            require(f'{k}: {v}' in flow_text, 'PINNED_ENGINE_DRIFT:' + k)
        for spec in NODE24_ACTIONS:
            require(spec in flow_text, 'NODE24_ACTION_MISSING:' + spec.split('@')[0])
        legacy = (root / '.github/workflows/build.yml').read_text()
        for spec in NODE24_ACTIONS:
            require(spec in legacy, 'LEGACY_NODE24_ACTION_MISSING:' + spec.split('@')[0])
        require(not any(x in legacy for x in (
            'actions/checkout@v4', 'actions/setup-java@v4',
            'gradle/actions/setup-gradle@v4', 'actions/upload-artifact@v4',
            'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02')),
            'LEGACY_NODE20_ACTION_NOT_MIGRATED')
        require(not any(x in flow_text for x in (
            'actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683',
            'android-actions/setup-android@v3',
            'gradle/actions/setup-gradle@v4',
            'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02')),
            'NODE20_MANUAL_WORKFLOW_NOT_MIGRATED')
    except OSError:
        issues.append('MANUAL_WORKFLOW_MISSING')
    try:
        ci = (root / '.github/workflows/devtool-source-contract.yml').read_text()
        require('Pinned A05/A07 config parser regression' in ci,
                'MISSING_EXACT_PINNED_DEVTOOL_PARSER_CI')
    except OSError:
        issues.append('SOURCE_CI_MISSING')
    try:
        props=(root/'gradle/wrapper/gradle-wrapper.properties').read_text()
        require(re.search(r'(?m)^distributionSha256Sum='+CHECKSUM+r'$',props) is not None,
                'UNPINNED_GRADLE_DISTRIBUTION')
        require('gradle-8.11.1-bin.zip' in props, 'GRADLE_VERSION_CHANGED')
    except OSError:
        issues.append('GRADLE_WRAPPER_PROPERTIES_MISSING')
    for required in ('.github/workflows/'+WORKFLOW,'.github/workflows/devtool-source-contract.yml'):
        require((root/required).is_file(), 'MISSING_WORKFLOW:' + required)
    for workflow_name in ('build','full','device'):
        require(workflow_name in flows, 'ORIGINAL_WORKFLOW_MISSING:'+workflow_name)
    require('storage-alias-source' in host_refs, 'MISSING_STORAGE_ALIAS_GATE')
    # Signing/source identity remains delegated to the established A07 workflow;
    # no source-only job is allowed to claim authenticated Android artifacts.
    require(jobs.get('storage-alias-source',{}).get('execution_environment') == 'native',
            'STORAGE_GATE_MUST_BE_HOST_NATIVE')
    # Do not imply R36 can be activated: Cinderbox produces a versioned APK
    # and the provider currently requires single-segment [A-Za-z0-9_-]+.apk.
    return {
        'schema_version': 1,
        'kind': 'cinderbox.devtool.offline-consumer-audit',
        'ok': not issues,
        'issues': sorted(set(issues)),
        'config_sha256': hashlib.sha256(data).hexdigest(),
        'jobs': len(jobs), 'workflows': len(flows), 'wrapper_commands': len(cmds),
        'host_graph_nodes': len(host_flow),
        'gradle_executed': False,
        'github_dispatch_performed': False,
        'apk_qualified': False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--json', action='store_true')
    p.add_argument('--repo', type=Path, default=ROOT)
    a = p.parse_args()
    outcome = audit(a.repo)
    if a.json:
        print(json.dumps(outcome,sort_keys=True,indent=2))
    else:
        print('PASS_CINDERBOX_DEVTOOL_SOURCE_CONTRACT' if outcome['ok'] else
              'FAIL_CINDERBOX_DEVTOOL_SOURCE_CONTRACT: '+', '.join(outcome['issues']))
    return 0 if outcome['ok'] else 2


if __name__ == '__main__':
    sys.exit(main())
