#!/usr/bin/env python3
"""Source and safety guard for UX-09B4; deterministic, non-mutating."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REQUIRED=(
 'app/src/androidTest/java/com/sdvsync/ui/ux/UxNativeFixtureCaptureTest.kt',
 'scripts/devtool/ux09b3_emulator_ci.sh',
 '.github/workflows/cinderbox-ux09b3-presentation-fixtures.yml',
 'scripts/devtool/ux09b4_visual_audit.py','scripts/devtool/ux09b4_gate.py',
 'scripts/devtool/test_ux09b4_gate.py',
 'design/cinderbox/02_CONTRACT/ux-contract.json',
 'design/cinderbox/02_CONTRACT/browser-layout-golden.json',
 'docs/security/M3_RELEASE_POLICY.json',
 'app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt',
 'app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt'
)
def read(root,name):
    p=root/name
    assert p.is_file() and not p.is_symlink(),'UX09B4_MISSING_OR_SYMLINK:'+name
    return p.read_text()
def check(root:Path=ROOT)->dict:
    root=Path(root)
    content={f:read(root,f) for f in REQUIRED}
    kt=content[REQUIRED[0]];script=content[REQUIRED[1]];wf=content[REQUIRED[2]];audit=content[REQUIRED[3]]
    assert kt.count('windowInsetsPadding(WindowInsets.statusBars)')==2,'UX09B4_STATUS_INSETS_UNSAFE'
    for x in ('UX09B4_STATUS_BAR_OVERLAP','content_top_px','status_bar_safe_area_asserted',
              'isolated-fixture-compose-statusBars', 'rule.onRoot().captureToImage()',
              'UX09B3_BLANK_DISPLAY_CAPTURE'):
        assert x in kt,'UX09B4_FIXTURE_SAFETY_GUARD_MISSING:'+x
    assert 'createComposeRule()' in kt and 'createAndroidComposeRule<MainActivity>()' not in kt
    assert 'ApprovedGameScreen(' in kt and 'ApprovedSavesScreen(' in kt and 'ApprovedModDetailContent(' in kt
    for x in ('restoreBackup(', 'deleteRecursively(', 'startDownload(', 'requestShizukuPermission(',
              'setSession(', 'saveCredentials(', 'getExternalStorageDirectory(', '/storage/emulated/0/'):
        assert x not in kt,'UX09B4_FORBIDDEN_UI_FIXTURE:'+x
    assert 'python3 -B scripts/devtool/ux09b4_visual_audit.py' in script
    assert 'bash scripts/devtool/ux09b2_emulator_ci.sh' in script
    assert 'UX09B3_24_CANDIDATE_SCREENSHOTS_NOT_VISUAL_ACCEPTANCE' in script
    assert 'scripts/devtool/ux09b4_gate.py' in wf
    assert "test_ux09b4_gate.py" in wf
    assert 'api-level: 36' in wf and 'if: always()' in wf
    assert 'permissions:\n  contents: read' in wf
    for claim in ("'native_goldens_approved':False", "'native_pixel_parity_verified':False",
                  "'real_mainactivity_cases':21", "'isolated_presentation_fixture_cases':3",
                  "'release_enabled':False", "'physical_device_qualified':False"):
        assert claim in audit,'UX09B4_VISUAL_REPORT_FALSE_CLAIM_MISSING:'+claim
    assert 'UX09B4_STATUS_BAR_OVERLAP' in audit and 'UX09B4_MATRIX_INCOMPLETE' in audit
    c=json.loads(content[REQUIRED[6]]);ref=root/'design/cinderbox'/c['reference']['path']
    assert c['reference']['sole_theme']=='dark' and c['screenshot_cases']['count']==24
    assert ref.is_file() and not ref.is_symlink()
    assert hashlib.sha256(ref.read_bytes()).hexdigest()==c['reference']['sha256'],'UX09B4_REFERENCE_DRIFT'
    assert len(json.loads(content[REQUIRED[7]]))==24
    policy=json.loads(content[REQUIRED[8]])
    for k in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        assert policy[k] is False,'UX09B4_RELEASE_POLICY_DRIFT:'+k
    assert ': Boolean = false' in content[REQUIRED[9]]
    coordinator=content[REQUIRED[10]]
    assert 'const val LIVE_UPDATES_ENABLED: Boolean = false' in coordinator
    assert 'const val DEVICE_ACCEPTED: Boolean = false' in coordinator
    return {'result':'UX09B4_SOURCE_AND_STATUS_INSET_PASS','captured_reference_cases':24,
            'actual_native_routes':21,'test_only_composable_previews':3,
            'native_goldens_approved':False,'release_enabled':False}
if __name__=='__main__':
    try: print(json.dumps(check(),sort_keys=True))
    except (OSError,AssertionError,ValueError,KeyError) as exc:
        print('UX09B4_SOURCE_REFUSED:'+str(exc),file=sys.stderr)
        raise SystemExit(1)
