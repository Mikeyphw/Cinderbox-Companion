#!/usr/bin/env python3
"""M17 offline UI/lifecycle tests on an explicitly authorized Android device.

No automatic install, uninstall, data clear, root escalation, or game path access.
Tests launch the real Activity; run ONLY on an intentionally signed-out test profile.
Reuses the proven M14 source/CI/APK attestation checks but runs ONLY the M17 class.
A PASS never qualifies publishing or release builds.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import tempfile

import m14_device_qualification as m14

REPO = m14.REPO
CLASS = 'com.sdvsync.qualification.M17OfflineUiDeviceTest'
TESTS = frozenset((
    'signedOutSettingsAreAccessibleWithoutSteamLogin',
    'operationCenterNavigationIsReadOnly',
    'activityRecreationPreservesOfflineSettingsNavigation',
    'operationCenterBackReturnsToSettingsAfterRefresh',
))
M17_CI_STEP = 'M17 Android UI and lifecycle qualification regressions'


def verify_m17_ci(run, jobs, head):
    m14.verify_ci(run, jobs, head)
    steps = jobs.get('jobs', [{}])[0].get('steps', [])
    successful = {s.get('name') for s in steps if s.get('conclusion') == 'success'}
    m14.require(M17_CI_STEP in successful, 'M17_CI_STEP_INCOMPLETE')
    m14.require(run.get('head_branch') in ('feature/m17-android-ui-lifecycle', 'master'),
                'M17_WRONG_CI_BRANCH')



def sanitized_failure_sites(output: str):
    """Summarize only allowlisted failure categories and M17 test line numbers.

    No raw Android instrumentation output, stack traces, user data, device IDs,
    file paths, credentials, or assertion messages are persisted in the report.
    """
    import re
    categories = (
        ('ESPRESSO_INPUT_MANAGER_REFLECTION',
         ('NoSuchMethodException: android.hardware.input.InputManager.getInstance',)),
        ('FRAMEWORK_REFLECTIVE_METHOD_MISSING', ('NoSuchMethodException',)),
        ('NO_COMPOSE_HIERARCHY', ('No compose hierarchies found', 'No compose hierarchies')),
        ('NODE_NOT_FOUND', ('NoMatchingNodeException', 'Failed to assert the following', 'No node found')),
        ('NODE_OFFSCREEN', ('Failed to perform a click', 'not displayed', 'not visible', 'does not support scroll')),
        ('ACTIVITY_LAUNCH', ('ActivityNotFoundException', 'Unable to resume activity', 'Failed to launch activity')),
        ('TEST_ASSERTION', ('AssertionError', 'AssertionFailedError')),
        ('TEST_EXCEPTION', ('Exception', 'Error')),
    )
    failures = {}
    fields = []
    reading_stack = False
    def flush(status):
        if status not in (-1, -2):
            return
        test = next((value for key, value in fields if key == 'test' and value in TESTS), None)
        if test is None:
            return
        stack = ' '.join(value for key, value in fields if key == 'stack')
        category = next((kind for kind, needles in categories
                         if any(token in stack for token in needles)), 'UNKNOWN')
        # Source-relative numeric line only; NEVER persist the stack text.
        match = re.search(r'M17OfflineUiDeviceTest\.kt:(\d{1,4})', stack)
        line = int(match.group(1)) if match else None
        failures[test] = {'category': category, 'test_line': line}
    for line in output.splitlines():
        if line.startswith('INSTRUMENTATION_STATUS: '):
            body = line[len('INSTRUMENTATION_STATUS: '):]
            reading_stack = False
            if '=' in body:
                key, value = body.split('=', 1)
                if key in ('test', 'stack'):
                    fields.append((key, value))
                reading_stack = key == 'stack'
        elif line.startswith('INSTRUMENTATION_STATUS_CODE: '):
            reading_stack = False
            try:
                code = int(line.rsplit(': ', 1)[-1])
            except ValueError:
                code = None
            flush(code)
            fields.clear()
        elif reading_stack:
            # JUnit emits multiline stack continuations without the STATUS prefix.
            # Keep them only in memory, and discard everything except allowlisted
            # category and M17 source-relative line number.
            fields.append(('stack', line))
    return failures


def run(args):
    report = {
        'schema_version': 1, 'producer': 'cinderbox-m17-device',
        'scope': 'explicit-debug-real-ui-signed-out-test-profile',
        'repository': REPO, 'github_run_id': args.run_id,
        'source_commit': None, 'runner_source_commit': None,
        'ci_checkout_commit': None, 'ci_checkout_ref': None,
        'ci': 'NOT_RUN', 'apk_sha256': None, 'test_apk_sha256': None,
        'transport': args.transport, 'device': None,
        'install': 'NOT_RUN', 'instrumentation': 'NOT_RUN',
        'launch': 'NOT_RUN', 'm14_reexecuted': False, 'm15_reexecuted': False,
        'overall': 'INCOMPLETE', 'failure_code': None,
        'device_qualified': False, 'release_qualified': False,
        'publication_allowed': False, 'automatic_device_install': False,
        'automatic_uninstall': False, 'live_ui_opt_in': False,
    }
    try:
        m14.require(args.ui_opt_in, 'LIVE_UI_REQUIRES_EXPLICIT_FLAG')
        report['live_ui_opt_in'] = True
        m14.require(args.install, 'INSTALL_REQUIRES_EXPLICIT_FLAG')
        repo = args.repo.resolve()
        local_head = m14.git_head(repo)
        # A local edit to the qualification runner or its target tests must not
        # be presented as source-bound CI evidence from an immutable commit.
        tracked = ('scripts/devtool/m14_device_qualification.py',
                   'scripts/devtool/m17_device_qualification.py',
                   'app/src/androidTest/java/com/sdvsync/qualification/M17OfflineUiDeviceTest.kt')
        dirty = m14.command(['git', '-C', str(repo), 'status', '--porcelain', '--', *tracked]).strip()
        m14.require(not dirty, 'LOCAL_QUALIFIER_MODIFIED')
        head = args.ci_head or local_head
        m14.require(m14.SHA40.fullmatch(head or '') is not None, 'INVALID_CI_HEAD')
        report['runner_source_commit'] = local_head
        report['source_commit'] = head
        m14.require(args.run_id > 0, 'INVALID_RUN_ID')
        run_data = m14.json_from_gh([f'repos/{REPO}/actions/runs/{args.run_id}'])
        jobs = m14.json_from_gh([f'repos/{REPO}/actions/runs/{args.run_id}/jobs?per_page=100'])
        verify_m17_ci(run_data, jobs, head)
        with tempfile.TemporaryDirectory(prefix='cinderbox-m17-') as directory:
            temp = Path(directory)
            main = temp / 'debug'
            tests = temp / 'instrumentation'
            main.mkdir()
            tests.mkdir()
            m14.command(['gh', 'run', 'download', str(args.run_id), '--repo', REPO,
                         '--name', 'debug-apk', '--dir', str(main)], timeout=240)
            # The M14/M17 APK is built once by the existing CI Gradle task.
            m14.command(['gh', 'run', 'download', str(args.run_id), '--repo', REPO,
                         '--name', 'm14-androidtest-apk', '--dir', str(tests)], timeout=240)
            provenance = m14.read_json(main / 'M3_PROVENANCE.json')
            ci_commit, ci_ref = m14.verified_ci_checkout(
                run_data, head, artifact_commit=provenance.get('source_commit'),
                artifact_ref=provenance.get('source_ref'))
            apk, test_apk, digest, test_digest = m14.verify_artifacts(
                main, tests, ci_commit, source_ref=ci_ref, run_id=args.run_id)
            report['ci'] = 'PASS'
            report['ci_checkout_commit'] = ci_commit
            report['ci_checkout_ref'] = ci_ref
            report['apk_sha256'] = digest
            report['test_apk_sha256'] = test_digest
            device = m14.Transport(args.transport)
            report['device'] = device.device_info()
            app_installed = device.installed(m14.PACKAGE)
            test_installed = device.installed(m14.TEST_PACKAGE)
            m14.require((not app_installed and not test_installed) or args.allow_replace,
                        'EXISTING_INSTALL_REQUIRES_ALLOW_REPLACE')
            report['install'] = 'ATTEMPTED'
            installed = device.install(apk, replace=app_installed)
            m14.require('Success' in installed.splitlines(), 'APP_PACKAGE_INSTALL_FAILED')
            m14.require(device.installed(m14.PACKAGE), 'APP_INSTALL_NOT_CONFIRMED')
            report['install'] = 'APP_INSTALLED_TEST_PENDING'
            installed = device.install(test_apk, replace=test_installed, test=True)
            m14.require('Success' in installed.splitlines(), 'TEST_PACKAGE_INSTALL_FAILED')
            m14.require(device.installed(m14.TEST_PACKAGE), 'TEST_INSTALL_NOT_CONFIRMED')
            report['install'] = 'PASS'
            report['instrumentation'] = 'ATTEMPTED'
            raw_instrumentation = device.instrument(test_class=CLASS)
            try:
                report['instrumentation'] = m14.parse_instrumentation(
                    raw_instrumentation, tests=TESTS)
            except m14.DeviceGateError:
                # Fail closed, retaining only sanitized error category and a
                # test-local source line; never write raw instrumentation logs.
                report['failure_diagnostics'] = sanitized_failure_sites(raw_instrumentation)
                raise
            report['overall'] = 'PASS_REAL_UI_LIFECYCLE_AUTOMATION'
    except m14.DeviceGateError as error:
        report['failure_code'] = error.code
        if error.case_summary is not None:
            report['instrumentation'] = error.case_summary
        report['overall'] = 'FAILED_OR_BLOCKED'
    except Exception:
        report['failure_code'] = 'UNEXPECTED_FAILURE'
        report['overall'] = 'FAILED_OR_BLOCKED'
    m14.write_report(args.output, report)
    print(json.dumps({'overall': report['overall'], 'failure_code': report['failure_code'],
                      'report': str(args.output)}, sort_keys=True))
    return 0 if report['overall'] == 'PASS_REAL_UI_LIFECYCLE_AUTOMATION' else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument('--run-id', type=int, required=True)
    p.add_argument('--ci-head', default=None, help='Explicit historical CI head, provenance checked')
    p.add_argument('--transport', choices=('adb', 'termux-root'), required=True)
    p.add_argument('--ui-opt-in', action='store_true', help='Explicit consent to launch real app UI on a signed-out test profile')
    p.add_argument('--install', action='store_true', help='Explicit opt-in to install two CI APKs')
    p.add_argument('--allow-replace', action='store_true', help='Explicit opt-in to matching-signature replacement')
    p.add_argument('--output', type=Path, required=True)
    return run(p.parse_args(argv))


if __name__ == '__main__':
    sys.exit(main())
