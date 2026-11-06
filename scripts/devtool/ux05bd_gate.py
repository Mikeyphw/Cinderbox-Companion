#!/usr/bin/env python3
"""UX-05B-D code/source safety gate. Not a substitute for native runtime tests."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]

def read(p):
    f=ROOT/p
    assert f.is_file() and not f.is_symlink(),f'UX05BD_MISSING:{p}'
    return f.read_text()

def check():
    screen=read('app/src/main/java/com/sdvsync/ui/screens/ApprovedModDetailScreen.kt')
    report=read('app/src/main/java/com/sdvsync/mods/ModRequirementsAssessor.kt')
    vm=read('app/src/main/java/com/sdvsync/ui/viewmodels/ModDetailViewModel.kt')
    main=read('app/src/main/java/com/sdvsync/MainActivity.kt')
    old=read('app/src/main/java/com/sdvsync/ui/screens/ModDetailScreen.kt')
    instrument=read('app/src/androidTest/java/com/sdvsync/qualification/UX05DetailVisualDeviceTest.kt')
    visual=read('scripts/devtool/ux05bd_visual_check.py')
    reference=read('scripts/devtool/ux05bd_reference_render.py')
    emulator=read('scripts/devtool/ux05bd_emulator_ci.sh')
    workflow=read('.github/workflows/cinderbox-ux05bd.yml')
    policy=json.loads(read('docs/security/M3_RELEASE_POLICY.json'))
    for text in ('cinderbox.screen.mod-detail','cinderbox.mod-detail.cover',
                 'cinderbox.mod-detail.compatibility','At a glance','Compatibility',
                 'Files & versions','Review files & downloads','StardewBottomBar('):
        assert text in screen, 'UX05BD_DETAIL_MISSING:'+text
    for text in ('ModCompatibility.atLeast(', 'RequirementVerdict.UNKNOWN',
                 'RequirementVerdict.BLOCKED','Installed SMAPI manifests',
                 'Android compatibility','Game version','SMAPI runtime'):
        assert text in report, 'UX05BD_EVIDENCE_MISSING:'+text
    assert 'ModRequirementsAssessor.assess(mod, inventory)' in vm
    assert 'files = fileList' in vm
    assert main.count('composable("mod_detail/{modId}/{source}")')==0  # route uses route=
    assert main.count('route = "mod_detail/{modId}/{source}"')==1
    assert main.count('route = "mod_detail_advanced/{modId}/{source}"')==1
    assert 'ApprovedModDetailScreen(' in main and 'ModDetailScreen(' in main
    assert 'viewModel.installFile(file.fileId)' in old
    assert 'ux05bd-detail-fixture.png' in instrument
    assert "ImageChops.difference" in visual
    assert "reference.size==(args.expected_width,args.expected_height)" in visual
    assert "contract['reference']['sha256']" in reference
    assert 'ux05bd-anchors-${width}x${height}.json' in emulator
    assert '--expected-width "$width" --expected-height "$height"' in workflow
    assert 'ux05bd_reference_render.py' in workflow
    assert 'ux05bd-detail-393x852.png' not in workflow or 'ux05bd-detail-${width}x${height}.png' in workflow
    for dangerous in ('startDownload(', 'installFile(', 'deleteRecursively(',
                      'Runtime.getRuntime()', 'requestShizukuPermission(', 'File('):
        assert dangerous not in screen, 'UX05BD_UNSAFE_PRESENTATION:'+dangerous
    for setting in ('release_enabled','publication_enabled',
                    'automatic_device_install','device_qualification_complete'):
        assert policy[setting] is False,'UX05BD_RELEASE_GATE_CHANGED:'+setting
    read('app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt')
    print('UX05BD_SOURCE_AND_RELEASE_SAFETY_PASS')
    return True

if __name__=='__main__':check()
