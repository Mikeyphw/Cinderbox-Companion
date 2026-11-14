#!/usr/bin/env python3
"""LAB03B source-only security and hosted workflow contract (never physical proof)."""
from __future__ import annotations
from pathlib import Path
import re
import sys
if sys.flags.optimize:
    raise SystemExit('LAB03B_PYTHON_OPTIMIZATION_REFUSED')
ROOT=Path(__file__).resolve().parents[2]
class Refused(Exception):pass
def need(ok, why):
    if not ok:raise Refused(why)
def check(root=ROOT):
    paths={
     'probe':'scripts/devtool/cbnx06_lab03b_readonly.py',
     'tests':'scripts/devtool/cbnx06_lab03b_tests.py',
     'workflow':'.github/workflows/cbnx06-lab03b-readonly.yml',
     'lab_workflow':'.github/workflows/cbnx06-full-cinderbox-lab.yml',
     'doc':'docs/CBNX06_LAB03B_PHYSICAL_READ_ONLY_AND_PAIRING.md',
    }
    contents={}
    for key,path in paths.items():
        p=root/path
        need(p.is_file() and not p.is_symlink(),'LAB03B_REQUIRED_SOURCE_MISSING_OR_LINKED:'+path)
        contents[key]=p.read_text(encoding='utf8')
    p=contents['probe']
    for anchor in ("LAB = 'com.sdvsync.cbnx06lab'", "PROD = 'com.sdvsync'",
         "PREFS = 'shared_prefs/cbnx03b_pairing_inbox.xml'",
         "'ro.build.version.sdk'", "'ro.kernel.qemu'", "'ro.boot.qemu'",
         'LAB_INSTALLED_APK_BYTES_DIFFER_FROM_HOSTED',
         'LAB_INBOX_SYMLINK_REFUSED', 'PHYSICAL_PACKAGE_IDENTITY_CHANGED',
         'production_game_unchanged_proven', 'browser_extension_installed_proven',
         'live_browser_pairing_proven', 'release_qualified',
         'new_exact_private_inbox_request_observed',
         "'source_sha') == args.expected_android_sha",
         "'browser_source_sha') == args.expected_browser_sha",
         "'shell', 'run-as', LAB, 'cat', PREFS",
         "'shell', 'pm', 'path', package", "'shell', 'sha256sum', path"):
        need(anchor in p,'LAB03B_READ_ONLY_GUARD_MISSING:'+anchor)
    # No mutation of any Android package, network access or personally-owned game roots.
    for forbidden in ("'install'", "'uninstall'", "'clear'", "'am', 'start'",
        "'input',", "'su'", "'grant'", "'mkdir'", "'rm'", "'reboot'",
        'requests.post(', 'urllib.request.urlopen(',
        '/storage/emulated/0/StardewValley'):
        need(forbidden not in p,'LAB03B_FORBIDDEN_DEVICE_CAPABILITY:'+forbidden)
    need('b\'<!DOCTYPE\'' in p and 'zipfile.ZipFile(xpi)' in p,
         'LAB03B_HOSTILE_INPUT_GUARDS_MISSING')
    w=contents['workflow']
    for anchor in ('pull_request:', 'workflow_dispatch:',
        'permissions:\n  contents: read',
        'python3 -B scripts/devtool/cbnx06_lab03b_source_gate.py',
        'python3 -B scripts/devtool/cbnx06_lab03b_tests.py',
        'timeout-minutes: 15', 'actions/checkout@'):
        need(anchor in w,'LAB03B_WORKFLOW_GUARD_MISSING:'+anchor)
    full=contents['lab_workflow']
    for anchor in ("'scripts/devtool/cbnx06_lab03b_*.py'",
        'python3 -B scripts/devtool/cbnx06_lab03b_source_gate.py',
        'python3 -B scripts/devtool/cbnx06_lab03b_tests.py',
        ':app:assembleCbnxLab'):
        need(anchor in full,'LAB03B_FULL_LAB_BUILD_NOT_TRIGGERED:'+anchor)
    tests=contents['tests']
    need(tests.count('    def test_')>=21, 'LAB03B_NEGATIVE_TEST_ROSTER_TOO_SMALL')
    for anchor in ('test_emulator_refused', 'test_wrong_lab_bytes_refused',
        'test_xpi_embedded_production_port_refused', 'test_fresh_exact_inbox_is_observation_not_browser_proof',
        'test_signed_claim_not_accepted_from_unsigned_artifact'):
        need(anchor in tests,'LAB03B_NEGATIVE_TEST_MISSING:'+anchor)
    need('manual' in contents['doc'].lower() and 'unsigned' in contents['doc'].lower(),
         'LAB03B_MANUAL_BROWSER_REQUIREMENTS_MISSING')
    print('CBNX06_LAB03B_READ_ONLY_SOURCE_SECURITY_AND_HOSTED_GATE_PASS')
if __name__ == '__main__':
    try:check()
    except (Refused,OSError,UnicodeError,ValueError) as e:
        print('CBNX06_LAB03B_SOURCE_REFUSED:'+str(e),file=sys.stderr)
        raise SystemExit(2)
