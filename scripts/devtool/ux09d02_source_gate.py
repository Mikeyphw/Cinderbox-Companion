#!/usr/bin/env python3
"""Source-only checks for UX09D02; always run legacy safety gates too."""
from __future__ import annotations
import pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
TEST='app/src/androidTest/java/com/sdvsync/ui/ux/Ux09D02RealRouteEvidenceTest.kt'
SHELL='scripts/devtool/ux09d02_emulator_ci.sh'
REPORT='scripts/devtool/ux09d02_report.py'
WORKFLOW='.github/workflows/cinderbox-ux09d02-real-offline-evidence.yml'


def check(root=ROOT):
    kt=(root/TEST).read_text()
    sh=(root/SHELL).read_text()
    rep=(root/REPORT).read_text()
    ci=(root/WORKFLOW).read_text()
    for needle in ('createAndroidComposeRule<MainActivity>()','cinderbox.screen.home',
                   'cinderbox.screen.game','cinderbox.screen.advanced-mods',
                   'cinderbox.steam-login.screen','cinderbox.screen.operation-center',
                   'cinderbox.advanced-mods.back','cinderbox.operation-center.back',
                   'Continue offline','Espresso.pressBack()','font in 0.98f..1.02f'):
        assert needle in kt, 'UX09D02_TEST_MISSING:'+needle
    assert 'performScrollToNode' in kt and 'cinderbox.mods.advanced' in kt
    assert 'onNodeWithTag("cinderbox.more.steam-action").performClick()' in kt
    for needle in ('ro.kernel.qemu','ro.build.version.sdk','== 36','svc wifi disable',
                   'svc data disable','wm density 320','font_scale 1.0','OK (4 tests)',
                   'INSTRUMENTATION_CODE: -1','UX09D02_FAILURE.txt'):
        assert needle in sh, 'UX09D02_EMULATOR_SAFETY_MISSING:'+needle
    for needle in ('image.verify()','image.load()','UX09D02_MISSING_EVIDENCE',
                   'UX09D02_BLANK_SCREEN','UX09D02_DARK_STATUS_ICONS',
                   "'native_goldens_approved':False","'physical_device_qualified':False"):
        assert needle in rep, 'UX09D02_REPORT_MISSING:'+needle
    assert 'Pillow==11.3.0' in ci and 'android-emulator-runner@' in ci
    assert 'test_ux09d02_png_audit.py' in ci
    assert 'test_m4_local_first.py' in ci and 'ux09d01_gate.py' in ci
    assert 'assembleDebugAndroidTest' in ci and 'workflow_dispatch:' in ci
    print('UX09D02_ADD_ONLY_REAL_ROUTE_SOURCE_GATE_PASS')

if __name__=='__main__':
    check()
