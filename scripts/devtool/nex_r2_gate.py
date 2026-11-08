#!/usr/bin/env python3
"""Fail-closed read-only NEX-R2 native presentation and release source contracts."""
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def check(root: Path = ROOT) -> list[str]:
    errors = []
    display = (root/'app/src/main/java/com/sdvsync/mods/api/NexR2Display.kt').read_text()
    cards = (root/'app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt').read_text()
    detail = (root/'app/src/main/java/com/sdvsync/ui/screens/ApprovedModDetailScreen.kt').read_text()
    ui_test = (root/'app/src/androidTest/java/com/sdvsync/ui/ux/NexR2RichDetailTest.kt').read_text()
    runner = (root/'scripts/devtool/nex_r2_emulator_ci.sh').read_text()
    ci = (root/'.github/workflows/nex-r2-rich-native.yml').read_text()
    policy = json.loads((root/'docs/security/M3_RELEASE_POLICY.json').read_text())
    required = {
        'display safety': all(x in display for x in ['fun text(', 'fun imageUrl(', 'fun groupedFiles(',
                          'fun dateUtc(']),
        'rich browse data': all(x in cards for x in ['NexR2Display.text(', 'NexR2Display.imageUrl(',
                            'NexR2Display.compactCount(', 'nex.r2.card']),
        'read-only detail': all(x in detail for x in ['NexR2Display.groupedFiles(files)',
                           'NexR2Display.text(', 'cinderbox.mod-detail.files',
                           'onReviewFiles', 'Compatibility not verified']),
        'synthetic fixture honesty': 'synthetic ui fixtures' in ui_test.lower() and 'assertEquals(0, reviews)' in ui_test,
        'native emulator': all(x in runner for x in ['ro.kernel.qemu','font_scale 1.0',
                          'NexR2RichDetailTest', 'NexR1NativeFiltersTest', 'r48_offline_gate.py']),
        'hosted CI': all(x in ci for x in ['api-level: 36', 'r48_offline_gate.py',
                             'nex_r2_emulator_ci.sh','nex_r2_gate.py', 'if: always()']),
    }
    for label, passed in required.items():
        if not passed: errors.append('NEX_R2_MISSING:' + label)
    for name in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        if policy.get(name) is not False: errors.append('NEX_R2_RELEASE_GATE:' + name)
    if 'svc data disable' in runner: errors.append('NEX_R2_OBSOLETE_CELLULAR_SHUTDOWN')
    if 'import androidx.compose.ui.test.assertExists' in ui_test:
        errors.append('NEX_R2_INVALID_COMPOSE_IMPORT:assertExists')
    # Do not allow a new browser engine, silent install, or privilege escalation in NEX-R2.
    for file in (display, ui_test):
        for token in ('WebView(', 'startDownload(', 'installPackage(', 'requestShizukuPermission(',
                      'Runtime.getRuntime(', 'getNexusApiKey('):
            if token in file: errors.append('NEX_R2_FORBIDDEN:' + token)
    return errors

if __name__=='__main__':
    errors = check()
    if errors:
        print('\n'.join(errors)); raise SystemExit(1)
    print('NEX_R2_READ_ONLY_SOURCE_GATE_PASS')
